from application.play_match_use_case import PlayMatchUseCase
from integration.match_repository import MatchRepository
from presentation.controllers.match_controller import (
    set_match_repository,
    set_match_use_case,
)


def compose() -> PlayMatchUseCase:
    repository = MatchRepository()
    return PlayMatchUseCase(repository)
