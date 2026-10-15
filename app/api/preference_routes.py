from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.schemas.preference_schema import (
    PreferenceCreate,
    PreferenceUpdate,
    PreferenceResponse,
)

from app.services.preference_service import (
    create_preferences,
    get_preferences,
    update_preferences,
)


# Prefix is registered in main.py
router = APIRouter(
    tags=["Preferences"]
)


@router.post(
    "/",
    response_model=PreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User Preferences",
    description="Creates notification preferences for a user.",
)
def create_user_preferences(
    preference: PreferenceCreate,
    db: Session = Depends(get_db),
):
    result = create_preferences(
        db,
        preference,
    )

    if isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result["message"],
        )

    return result


@router.get(
    "/{user_id}",
    response_model=PreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Preferences",
    description="Returns notification preferences for a specific user.",
)
def get_user_preferences(
    user_id: int,
    db: Session = Depends(get_db),
):
    preference = get_preferences(
        db,
        user_id,
    )

    if preference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not found",
        )

    return preference


@router.put(
    "/{user_id}",
    response_model=PreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Preferences",
    description="Updates notification preferences for a specific user.",
)
def update_user_preferences(
    user_id: int,
    preference: PreferenceUpdate,
    db: Session = Depends(get_db),
):
    updated = update_preferences(
        db,
        user_id,
        preference,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not found",
        )

    return updated