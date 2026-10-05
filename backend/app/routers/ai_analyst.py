import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services.ai_analyst import (
    AIAnalystConfigurationError,
    AIAnalystInvalidToolCallError,
    AIAnalystProviderError,
    AIAnalystToolExecutionError,
    AIAnalystToolLimitError,
    run_ai_analyst_query,
)
from app.services.analyst import AnalystValidationError
from app.services.daily_review import (
    DailyReviewCurrencyError,
    LocationNotFoundError,
)


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/ai-analyst",
    tags=["ai-analyst"],
)


@router.post(
    "/query",
    response_model=schemas.AIAnalystQueryResponse,
)
def query_ai_analyst(
    query: schemas.AIAnalystQueryRequest,
    db: Session = Depends(get_db),
) -> schemas.AIAnalystQueryResponse:
    """Answer a location-scoped question using deterministic Ledger tools."""

    try:
        return run_ai_analyst_query(db, query.location_id, query.question)
    except LocationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        AnalystValidationError,
        DailyReviewCurrencyError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except AIAnalystConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except (
        AIAnalystInvalidToolCallError,
        AIAnalystProviderError,
        AIAnalystToolLimitError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except AIAnalystToolExecutionError as error:
        logger.error("AI analyst Ledger tool failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
