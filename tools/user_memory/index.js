#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// use relative path, start from user directory
const CLAUDE_MD_PATH = path.join(os.homedir(), '.claude', 'CLAUDE.md');

class MemoryManager {
  constructor() {
    this.filePath = CLAUDE_MD_PATH;
    this.ensureMemorySection();
  }

  generateMemoryId() {
    // generate 16-digit string as ID
    const timestamp = Date.now().toString();
    const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    return timestamp + random;
  }

  ensureMemorySection() {
    // Create .claude directory if it doesn't exist
    const claudeDir = path.dirname(this.filePath);
    if (!fs.existsSync(claudeDir)) {
      fs.mkdirSync(claudeDir, { recursive: true });
      console.error(`Created directory: ${claudeDir}`);
    }
    
    // Create CLAUDE.md if it doesn't exist
    if (!fs.existsSync(this.filePath)) {
      const initialContent = `
Personal configurations and memories for Lain.

## MEMORIES
<!-- Memory section start -->
<!-- Memory section end -->
`;
      fs.writeFileSync(this.filePath, initialContent, 'utf-8');
      console.error(`Created CLAUDE.md at ${this.filePath}`);
      return;
    }
    
    // Add MEMORIES section if it doesn't exist
    let content = fs.readFileSync(this.filePath, 'utf-8');
    if (!content.includes('## MEMORIES')) {
      content += '\n\n## MEMORIES\n<!-- Memory section start -->\n<!-- Memory section end -->\n';
      fs.writeFileSync(this.filePath, content, 'utf-8');
    }
  }

  parseMemories() {
    const content = fs.readFileSync(this.filePath, 'utf-8');
    const memories = [];
    // match JSON format memory
    const regex = /\{"date":\s*"[^"]+",\s*"memory_id":\s*"(\d+)",\s*"memory":\s*"([^"]*)"\}/g;
    let match;
    
    while ((match = regex.exec(content)) !== null) {
      const fullMatch = match[0];
      try {
        const memoryObj = JSON.parse(fullMatch);
        memories.push(memoryObj);
      } catch (e) {
        console.error('Failed to parse memory:', e);
      }
    }
    return memories;
  }

  insertMemory(memory) {
    const content = fs.readFileSync(this.filePath, 'utf-8');
    const memoryId = this.generateMemoryId();
    
    // create standard format memory object
    const memoryObj = {
      date: new Date().toISOString().split('T')[0], // YYYY-MM-DD
      memory_id: memoryId,
      memory: memory.trim()
    };
    
    const newMemoryLine = JSON.stringify(memoryObj) + '\n';
    
    // insert new memory before memory region end marker
    const updatedContent = content.replace(
      '<!-- Memory section end -->',
      `${newMemoryLine}<!-- Memory section end -->`
    );
    
    fs.writeFileSync(this.filePath, updatedContent, 'utf-8');
    
    return { 
      success: true, 
      memory_id: memoryId,
      date: memoryObj.date,
      message: `Memory saved with ID: ${memoryId}`,
      content: memory.trim()
    };
  }

  updateMemory(memoryId, memory) {
    const content = fs.readFileSync(this.filePath, 'utf-8');
    const memories = this.parseMemories();
    
    // find target memory
    const targetMemory = memories.find(m => m.memory_id === memoryId);
    if (!targetMemory) {
      throw new Error(`Memory ${memoryId} does not exist`);
    }
    
    // create new memory object
    const updatedMemoryObj = {
      date: new Date().toISOString().split('T')[0], // update date
      memory_id: memoryId,
      memory: memory.trim()
    };
    
    // replace old memory
    const oldMemoryStr = JSON.stringify(targetMemory);
    const newMemoryStr = JSON.stringify(updatedMemoryObj);
    const updatedContent = content.replace(oldMemoryStr, newMemoryStr);
    
    fs.writeFileSync(this.filePath, updatedContent, 'utf-8');
    
    return { 
      success: true, 
      memory_id: memoryId,
      date: updatedMemoryObj.date,
      message: `Memory ${memoryId} has been updated`,
      old_content: targetMemory.memory,
      new_content: memory.trim()
    };
  }

  deleteMemory(memoryId) {
    const content = fs.readFileSync(this.filePath, 'utf-8');
    const memories = this.parseMemories();
    
    // find target memory
    const targetMemory = memories.find(m => m.memory_id === memoryId);
    if (!targetMemory) {
      throw new Error(`Memory ${memoryId} does not exist`);
    }
    
    // delete memory line (including newline)
    const memoryStr = JSON.stringify(targetMemory);
    const updatedContent = content.replace(memoryStr + '\n', '');
    
    fs.writeFileSync(this.filePath, updatedContent, 'utf-8');
    
    return { 
      success: true, 
      memory_id: memoryId,
      message: `Memory ${memoryId} has been deleted`,
      deleted_content: targetMemory.memory
    };
  }

  listMemories() {
    const memories = this.parseMemories();
    const memoryList = memories.map(m => ({
      date: m.date,
      memory_id: m.memory_id,
      content: m.memory.substring(0, 100) + (m.memory.length > 100 ? '...' : ''),
      length: m.memory.length
    }));
    
    return {
      success: true,
      total: memoryList.length,
      memories: memoryList
    };
  }
}

// create MCP server
const memoryManager = new MemoryManager();
const server = new Server(
  { 
    name: 'user-memory', 
    version: '1.0.0' 
  },
  { 
    capabilities: { 
      tools: {} 
    } 
  }
);

// register tool list
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'insert_memory',
        description: `Use this tool when the user explicitly expresses the intention to add or insert a new memory,
and it is clear they are consciously invoking Lain's memory capability. 
The 'memory' field represents a valuable piece of information extracted from the user's latest message 
that should be remembered from now on. The content must be:
- semantically complete,
- unambiguous,
- expressed as a declarative statement,
- combined with conversation context if necessary for clarity,
- and must not duplicate existing memory entries.`,
        inputSchema: {
          type: 'object',
          properties: {
            memory: { 
              type: 'string', 
              description: 'The declarative memory content to be inserted, derived from user intent. Must be semantically complete, unambiguous, and expressed as a declarative statement. Combined with conversation context if necessary for clarity.' 
            }
          },
          required: ['memory']
        }
      },
      {
        name: 'update_memory',
        description: `Use this tool when the user explicitly requests to change or overwrite an existing memory entry with factual conflict（e.g. old memory user is a girl, but current conversation context indicates that user is a boy）.
The 'memory_id' identifies the target memory to be updated, and the 'memory' field must replace its content.
The new memory content should be semantically complete, unambiguous, and expressed as a declarative statement.`,
        inputSchema: {
          type: 'object',
          properties: {
            memory_id: { 
              type: 'string',
              description: 'The unique identifier of the memory entry to be updated.'
            },
            memory: { 
              type: 'string',
              description: 'The revised declarative memory content that replaces the existing entry. Must be semantically complete, unambiguous, and expressed as a declarative statement. Combined with conversation context if necessary for clarity.'
            }
          },
          required: ['memory_id', 'memory']
        }
      },
      {
        name: 'delete_memory',
        description: `Use this tool when the user explicitly requests to forget, remove, or erase a specific memory entry. 
The operation is irreversible. The 'memory_id' uniquely identifies which memory to delete.`,
        inputSchema: {
          type: 'object',
          properties: {
            memory_id: { 
              type: 'string',
              description: 'The unique identifier of the memory entry to be deleted.'
            }
          },
          required: ['memory_id']
        }
      }
    ]
  };
});


// handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  try {
    let result;
    
    switch (name) {
      case 'insert_memory':
        result = memoryManager.insertMemory(args.memory);
        break;
        
      case 'update_memory':
        result = memoryManager.updateMemory(args.memory_id, args.memory);
        break;
        
      case 'delete_memory':
        result = memoryManager.deleteMemory(args.memory_id);
        break;
        
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify(result, null, 2)
      }]
    };
    
  } catch (error) {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({ 
          success: false,
          error: error.message,
          tool: name
        }, null, 2)
      }]
    };
  }
});

// start server
async function main() {
  console.error('Starting User Memory MCP Server...');
  console.error(`Memory file: ${CLAUDE_MD_PATH}`);
  
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  console.error('User Memory Server is running');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});