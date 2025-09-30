"""
Feishu Card Message Builder for LainNet
Supports JSON 2.0 structure with streaming updates
"""

import json
from typing import Dict, Any, Optional, List
from enum import Enum


class CardTemplate(Enum):
    """Card header template colors"""
    BLUE = "blue"
    WATHET = "wathet"
    TURQUOISE = "turquoise"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    CARMINE = "carmine"
    VIOLET = "violet"
    PURPLE = "purple"
    INDIGO = "indigo"
    GREY = "grey"
    DEFAULT = "default"


class CardStatus(Enum):
    """Lain status states"""
    BOOTING = "🤖 Lain 正在开机..."
    THINKING = "💭 正在思考..."
    GENERATING = "✨ 生成回复中..."
    COMPLETED = "✅ 回复完成"
    ERROR = "❌ 出现错误"


class CardBuilder:
    """Builder for creating and updating Feishu card messages"""
    
    @staticmethod
    def create_initial_card(status: CardStatus = CardStatus.BOOTING) -> Dict[str, Any]:
        """
        Create initial card with streaming mode enabled
        
        Args:
            status: Initial status to display
            
        Returns:
            Card JSON structure (2.0)
        """
        # Special card for booting state with images
        if status == CardStatus.BOOTING:
            return {
                "schema": "2.0",
                "config": {
                    "update_multi": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "Lain init"
                    },
                    "template": CardTemplate.BLUE.value
                },
                "body": {
                    "direction": "vertical",
                    "horizontal_spacing": "8px",
                    "vertical_spacing": "8px",
                    "horizontal_align": "left",
                    "vertical_align": "top",
                    "padding": "12px 12px 12px 12px",
                    "elements": [
                        {
                            "tag": "hr",
                            "margin": "0px 0px 0px 0px"
                        },
                        {
                            "tag": "img",
                            "img_key": "img_v3_02ql_11ee9aed-5157-471a-8b46-252b0820a27g",
                            "preview": True,
                            "transparent": False,
                            "scale_type": "crop_center",
                            "size": "stretch",
                            "alt": {
                                "tag": "plain_text",
                                "content": "正在开机中"
                            },
                            "corner_radius": "8px",
                            "margin": "4px 4px 4px 4px"
                        },
                        {
                            "tag": "img",
                            "img_key": "img_v3_02qk_63f010bb-33b8-4d73-979c-0b4ebe0f3b8g",
                            "preview": True,
                            "transparent": False,
                            "scale_type": "fit_horizontal",
                            "alt": {
                                "tag": "plain_text",
                                "content": "正在开机中"
                            },
                            "corner_radius": "8px",
                            "margin": "0px 0px 0px 0px"
                        },
                        {
                            "tag": "hr",
                            "margin": "0px 0px 0px 0px"
                        }
                    ]
                }
            }
        
        # Standard card for other states (also v2.0)
        return {
            "schema": "2.0",
            "config": {
                "update_multi": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "Lain"
                },
                "template": CardTemplate.BLUE.value
            },
            "body": {
                "direction": "vertical",
                "horizontal_spacing": "8px",
                "vertical_spacing": "8px",
                "horizontal_align": "left",
                "vertical_align": "top",
                "padding": "12px 12px 12px 12px",
                "elements": [{
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": status.value
                    }
                }]
            }
        }
    
    @staticmethod
    def create_status_card(status: CardStatus, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a status card with optional message
        
        Args:
            status: Current status
            message: Optional message to display in body
            
        Returns:
            Card JSON structure
        """
        card = CardBuilder.create_initial_card(status)
        
        if message:
            card["body"]["elements"] = [{
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": message
                }
            }]
        
        # Adjust template color based on status
        if status == CardStatus.ERROR:
            card["header"]["template"] = CardTemplate.RED.value
        elif status == CardStatus.COMPLETED:
            card["header"]["template"] = CardTemplate.GREEN.value
        elif status == CardStatus.THINKING:
            card["header"]["template"] = CardTemplate.INDIGO.value
        elif status == CardStatus.GENERATING:
            card["header"]["template"] = CardTemplate.TURQUOISE.value
            
        return card
    
    @staticmethod
    def create_response_card(content: str, status: CardStatus = CardStatus.GENERATING) -> Dict[str, Any]:
        """
        Create a card with AI response content
        
        Args:
            content: Response content (supports markdown)
            status: Current status
            
        Returns:
            Card JSON structure
        """
        card = {
            "schema": "2.0",
            "config": {
                "wide_screen_mode": True,
                "update_multi": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "Lain"
                },
                "template": CardTemplate.TURQUOISE.value if status == CardStatus.GENERATING else CardTemplate.GREEN.value
            },
            "body": {
                "direction": "vertical",
                "horizontal_spacing": "8px",
                "vertical_spacing": "8px",
                "horizontal_align": "left",
                "vertical_align": "top",
                "padding": "12px 12px 12px 12px",
                "elements": [{
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                }]
            }
        }
        
        return card
    
    @staticmethod
    def create_streaming_update(content: str, is_complete: bool = False) -> Dict[str, Any]:
        """
        Create a streaming update for the card
        
        Args:
            content: Current content to display
            is_complete: Whether the response is complete
            
        Returns:
            Card JSON structure for update
        """
        status = CardStatus.COMPLETED if is_complete else CardStatus.GENERATING
        return CardBuilder.create_response_card(content, status)
    
    @staticmethod
    def create_error_card(error_message: str) -> Dict[str, Any]:
        """
        Create an error card
        
        Args:
            error_message: Error message to display
            
        Returns:
            Card JSON structure
        """
        return CardBuilder.create_status_card(
            CardStatus.ERROR,
            f"**错误信息：**\n\n{error_message}\n\n请稍后重试或联系管理员。"
        )
    
    @staticmethod
    def add_metadata(card: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
        """
        Add metadata tags to the card header
        
        Args:
            card: Card JSON structure
            metadata: Metadata to add as tags
            
        Returns:
            Updated card JSON
        """
        if "header" not in card:
            card["header"] = {}
            
        tags = []
        colors = ["neutral", "blue", "turquoise", "green"]
        
        for i, (key, value) in enumerate(list(metadata.items())[:3]):  # Max 3 tags
            tags.append({
                "tag": "text_tag",
                "element_id": f"meta_{key}",
                "text": {
                    "tag": "plain_text",
                    "content": f"{key}: {value}"
                },
                "color": colors[i % len(colors)]
            })
        
        card["header"]["text_tag_list"] = tags
        return card
    
    @staticmethod
    def to_json_string(card: Dict[str, Any]) -> str:
        """
        Convert card dict to JSON string for API
        
        Args:
            card: Card dictionary
            
        Returns:
            JSON string
        """
        return json.dumps(card, ensure_ascii=False)