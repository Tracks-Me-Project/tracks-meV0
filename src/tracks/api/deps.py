from typing import Annotated

from fastapi import Depends, Path, Query
from pydantic import Field
from sqlalchemy.orm import Session

from tracks.clock import Clock, SystemClock
from tracks.db import get_session

# scope="function" : le commit a lieu AVANT l'envoi de la réponse. Par défaut FastAPI le fait après,
# et le client recevrait « succès » pour une écriture pas encore (ou jamais) enregistrée.
# Toutes les routes passent par DbSession pour partager la même session dans une requête.
DbSession = Annotated[Session, Depends(get_session, scope="function")]


def get_clock() -> Clock:
    # Dépendance remplaçable : les tests et la simulation injectent une horloge qu'ils contrôlent.
    return SystemClock()


# Limites techniques des entrées (pas des règles du jeu) : les montants sont des entiers 32 bits en
# base, et Postgres refuse le caractère nul dans un texte. Sans elles, ces valeurs donnent un 500.
MAX_INT = 2**31 - 1

Amount = Annotated[int, Field(gt=0, le=MAX_INT)]
Mbid = Annotated[str, Field(min_length=1, max_length=36, pattern=r"^[^\x00]+$")]
AuctionId = Annotated[int, Path(ge=1, le=MAX_INT)]
Offset = Annotated[int, Query(ge=0, le=MAX_INT)]
