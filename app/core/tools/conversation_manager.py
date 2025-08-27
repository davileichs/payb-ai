from typing import Dict, Any
from app.core.tools.base import BaseTool, ToolResult, register_tool
from app.core.conversation_manager import get_conversation_manager

class ConversationManagerTool(BaseTool):
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            action = kwargs.get("action", "stats")
            user_id = kwargs.get("user_id")
            channel_id = kwargs.get("channel_id")
            max_conversations = kwargs.get("max_conversations", None)  # No automatic cleanup
            
            conversation_manager = get_conversation_manager()
            
            if action == "cleanup":
                result = await self._cleanup_conversations(conversation_manager, max_conversations)
                return result
                
            elif action == "delete":
                if not user_id or not channel_id:
                    return ToolResult(
                        success=False,
                        error="User ID and Channel ID are required for delete action",
                        metadata={"tool_name": "ConversationManager"}
                    )
                result = await self._delete_conversation(conversation_manager, user_id, channel_id)
                return result
                
            elif action == "stats":
                result = self._get_stats(conversation_manager)
                return result
                
            elif action == "list":
                result = self._list_conversations(conversation_manager)
                return result
                
            elif action == "clear_all":
                result = await self._clear_all_conversations(conversation_manager)
                return result
                
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    metadata={"tool_name": "ConversationManager"}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "ConversationManager"}
            )
    
    async def _cleanup_conversations(self, conversation_manager, max_conversations: int) -> ToolResult:
        try:
            total_before = len(conversation_manager.conversations)
            conversation_manager.cleanup_conversations(max_conversations)
            total_after = len(conversation_manager.conversations)
            removed_count = total_before - total_after
            
            return ToolResult(
                success=True,
                data={
                    "message": f"Cleaned up conversations. Kept {total_after}, removed {removed_count}",
                    "conversations_before": total_before,
                    "conversations_after": total_after,
                    "removed_count": removed_count,
                    "max_conversations": max_conversations
                },
                metadata={"tool_name": "ConversationManager"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to cleanup conversations: {str(e)}",
                metadata={"tool_name": "ConversationManager"}
            )
    
    async def _delete_conversation(self, conversation_manager, user_id: str, channel_id: str) -> ToolResult:
        try:
            conversation_id = conversation_manager._generate_conversation_id(user_id, channel_id)
            
            if conversation_id in conversation_manager.conversations:
                del conversation_manager.conversations[conversation_id]
                
                try:
                    if hasattr(conversation_manager, 'redis_storage') and conversation_manager.redis_storage:
                        await conversation_manager.redis_storage.delete_conversation(conversation_id)
                except Exception:
                    pass  # Ignore Redis errors for this operation
                
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Successfully deleted conversation for user {user_id} in channel {channel_id}",
                        "user_id": user_id,
                        "channel_id": channel_id,
                        "conversation_id": conversation_id
                    },
                    metadata={"tool_name": "ConversationManager"}
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"Conversation not found for user {user_id} in channel {channel_id}",
                    metadata={"tool_name": "ConversationManager"}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to delete conversation: {str(e)}",
                metadata={"tool_name": "ConversationManager"}
            )
    
    def _get_stats(self, conversation_manager) -> ToolResult:
        try:
            stats = conversation_manager.get_conversation_stats()
            config = conversation_manager.get_configuration()
            
            return ToolResult(
                success=True,
                data={
                    "stats": stats,
                    "configuration": config,
                    "total_conversations": len(conversation_manager.conversations)
                },
                metadata={"tool_name": "ConversationManager"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to get conversation stats: {str(e)}",
                metadata={"tool_name": "ConversationManager"}
            )
    
    def _list_conversations(self, conversation_manager) -> ToolResult:
        try:
            conversations = []
            for conv_id, conversation in conversation_manager.conversations.items():
                conversations.append({
                    "conversation_id": conv_id,
                    "user_id": conversation.user_id,
                    "channel_id": conversation.channel_id,
                    "message_count": len(conversation.messages),
                    "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                    "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
                })
            
            return ToolResult(
                success=True,
                data={
                    "conversations": conversations,
                    "total_count": len(conversations)
                },
                metadata={"tool_name": "ConversationManager"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to list conversations: {str(e)}",
                metadata={"tool_name": "ConversationManager"}
            )
    
    async def _clear_all_conversations(self, conversation_manager) -> ToolResult:
        try:
            total_conversations = len(conversation_manager.conversations)
            conversation_manager.conversations.clear()
            
            # Also try to clear from Redis if available
            try:
                if hasattr(conversation_manager, 'redis_storage') and conversation_manager.redis_storage:
                    keys = await conversation_manager.redis_storage.get_conversation_keys()
                    for key in keys:
                        await conversation_manager.redis_storage.delete_conversation(key)
            except Exception:
                pass  # Ignore Redis errors for this operation
            
            return ToolResult(
                success=True,
                data={
                    "message": f"Cleared all {total_conversations} conversations",
                    "conversations_cleared": total_conversations
                },
                metadata={"tool_name": "ConversationManager"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to clear all conversations: {str(e)}",
                metadata={"tool_name": "ConversationManager"}
            )

# Register the tool automatically
register_tool(ConversationManagerTool())
