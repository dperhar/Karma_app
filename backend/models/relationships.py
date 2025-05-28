"""Define relationships between models."""

from sqlalchemy.orm import relationship


def setup_relationships():
    """Setup all model relationships."""
    # Import all models first
    from models.ai.ai_dialog import AIDialog
    from models.ai.ai_request import AIRequest
    from models.management.person import ManagementPerson
    from models.telegram_messenger.chat import TelegramMessengerChat
    from models.telegram_messenger.chat_user import TelegramMessengerChatUser
    from models.telegram_messenger.message import TelegramMessengerMessage
    from models.user.user import User

    # User relationships
    User.telegram_participants = relationship(
        "TelegramMessengerChatUser", back_populates="user"
    )
    User.telegram_chats = relationship("TelegramMessengerChat", back_populates="user")
    User.management_persons = relationship("ManagementPerson", back_populates="user")
    User.ai_dialogs = relationship("AIDialog", back_populates="user")
    User.ai_requests = relationship("AIRequest", back_populates="user")
    # ManagementPerson relationships
    ManagementPerson.user = relationship("User", back_populates="management_persons")
    ManagementPerson.telegram_participants = relationship(
        "TelegramMessengerChatUser", back_populates="management_person"
    )

    # TelegramMessengerChatUser relationships
    TelegramMessengerChatUser.user = relationship(
        "User", back_populates="telegram_participants"
    )
    TelegramMessengerChatUser.management_person = relationship(
        "ManagementPerson", back_populates="telegram_participants"
    )
    TelegramMessengerChatUser.chat = relationship(
        "TelegramMessengerChat", back_populates="participants"
    )
    TelegramMessengerChatUser.messages = relationship(
        "TelegramMessengerMessage", back_populates="sender"
    )

    # TelegramMessengerChat relationships
    TelegramMessengerChat.user = relationship("User", back_populates="telegram_chats")
    TelegramMessengerChat.participants = relationship(
        "TelegramMessengerChatUser", back_populates="chat"
    )
    TelegramMessengerChat.messages = relationship(
        "TelegramMessengerMessage", back_populates="chat"
    )
    TelegramMessengerChat.ai_dialogs = relationship("AIDialog", back_populates="chat")

    # TelegramMessengerMessage relationships
    TelegramMessengerMessage.chat = relationship(
        "TelegramMessengerChat", back_populates="messages"
    )
    TelegramMessengerMessage.sender = relationship(
        "TelegramMessengerChatUser", back_populates="messages"
    )

    # AIDialog relationships
    AIDialog.ai_requests = relationship("AIRequest", back_populates="dialog")
    AIDialog.user = relationship("User", back_populates="ai_dialogs")
    AIDialog.chat = relationship("TelegramMessengerChat", back_populates="ai_dialogs")

    # AIRequest relationships
    AIRequest.user = relationship("User", back_populates="ai_requests")
    AIRequest.dialog = relationship("AIDialog", back_populates="ai_requests")
