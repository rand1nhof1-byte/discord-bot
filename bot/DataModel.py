from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta


@dataclass
class Role:
    role_id: Optional[int]
    discord_role_id: str
    display_name: str

@dataclass
class TemplateOption:
    template_option_id: Optional[int]
    template_id: Optional[int]
    emoji: str
    option_text: str
    required_roles: str


@dataclass
class Template:
    template_id: Optional[int]
    name: str
    description: Optional[str]
    created_at: datetime = datetime.now()
    options: Optional[List[TemplateOption]] = None


@dataclass
class TemplateRequiredRole:
    template_option_id: int
    role_id: int


@dataclass
class PollOption:
    option_id: Optional[int]
    poll_id: Optional[int]
    emoji: str
    option_text: str
    required_roles: Optional[List["Role"]] = None


@dataclass
class Poll:
    poll_id: Optional[int]
    channel_id: int
    title: str
    description: Optional[str]
    message_id: Optional[int]
    created_at: datetime = datetime.now()
    is_active: bool = True
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    template_id: Optional[int] = None
    options: Optional[List[PollOption]] = None

    def ready_to_ping(self):
        return datetime.now() + timedelta(minutes=15) >= self.start_time

    def has_ended(self):
        end_time = self.start_time + timedelta(minutes=self.duration_minutes)
        return datetime.now() >= end_time

    def is_currently_active(self):
        return self.is_active and not self.has_ended()


@dataclass
class OptionRequiredRole:
    option_id: int
    role_id: int


@dataclass
class Vote:
    vote_id: Optional[int]
    poll_id: int
    option_id: int
    discord_user_id: int
    user_display_name: str
    voted_at: datetime = datetime.now()