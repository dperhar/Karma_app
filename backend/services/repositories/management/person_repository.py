"""Repository for management person operations."""

from typing import Optional

from sqlalchemy import select

from models.management.person import ManagementPerson
from services.base.base_repository import BaseRepository


class PersonRepository(BaseRepository):
    """Repository class for management person operations."""

    async def create_person(self, person: ManagementPerson) -> ManagementPerson:
        """Create a new person.

        Args:
            person: ManagementPerson object to create

        Returns:
            Created ManagementPerson object
        """
        async with self.get_session() as session:
            try:
                session.add(person)
                await session.commit()
                await session.refresh(person)
                self.logger.info(f"Successfully created person with id: {person.id}")
                return person
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating person: {e!s}", exc_info=True)
                raise

    async def get_person(self, person_id: str) -> Optional[ManagementPerson]:
        """Get person by ID.

        Args:
            person_id: Person ID

        Returns:
            ManagementPerson object or None if not found
        """
        async with self.get_session() as session:
            try:
                query = select(ManagementPerson).where(ManagementPerson.id == person_id)
                result = await session.execute(query)
                person = result.unique().scalar_one_or_none()
                if not person:
                    self.logger.info(f"Person not found with id: {person_id}")
                return person
            except Exception as e:
                self.logger.error(f"Error getting person: {e!s}", exc_info=True)
                raise

    async def get_person_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[ManagementPerson]:
        """Get person by Telegram ID.

        Args:
            telegram_id: Telegram ID

        Returns:
            ManagementPerson object or None if not found
        """
        async with self.get_session() as session:
            try:
                query = select(ManagementPerson).where(
                    ManagementPerson.telegram_id == telegram_id
                )
                result = await session.execute(query)
                persons = result.unique().scalars().all()
                if not persons:
                    self.logger.info(
                        f"Person not found with telegram_id: {telegram_id}"
                    )
                    return None
                if len(persons) > 1:
                    self.logger.warning(
                        f"Multiple persons found with telegram_id: {telegram_id}, using the first one"
                    )
                return persons[0]
            except Exception as e:
                self.logger.error(
                    f"Error getting person by telegram_id: {e!s}", exc_info=True
                )
                raise
