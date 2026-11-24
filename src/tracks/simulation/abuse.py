"""Tentatives d'abus de base, toutes via l'API et en requêtes simultanées. Chaque scénario
renvoie (réussi, détail) : « réussi » veut dire que le jeu a bien résisté."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import NamedTuple

from tracks.simulation.world import Player, World


class AbuseResult(NamedTuple):
    name: str
    resisted: bool
    detail: str


def _codes(responses) -> list[int]:
    return sorted(r.status_code for r in responses)


async def _me(world: World, p: Player) -> tuple[int, int]:
    data = (await world.call(p, "GET", "/me")).json()
    return data["available"], data["locked"]


async def _sell(world: World, seller: Player, start: int = 100, minutes: int = 60) -> int:
    body = {"recording_mbid": world.any_track(), "start_price": start, "duration_minutes": minutes}
    r = await world.call(seller, "POST", "/auctions", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seller_with_cards(world: World, tag: str, cards: int) -> Player:
    seller = await world.signup(world.unique_name(tag))
    world.give_cards(seller, world.any_track(), cards)
    return seller


def _bid(world: World, p: Player, auction_id: int, amount: int) -> Awaitable:
    return world.call(p, "POST", f"/auctions/{auction_id}/bids", json={"amount": amount})


async def double_spend(world: World) -> AbuseResult:
    """Un joueur mise 400 sur 5 enchères en même temps avec 1000 : seules 2 mises passent."""
    seller = await _seller_with_cards(world, "ds-vendeur", 5)
    ids = [await _sell(world, seller) for _ in range(5)]
    buyer = await world.signup(world.unique_name("ds-acheteur"))
    codes = _codes(await asyncio.gather(*[_bid(world, buyer, i, 400) for i in ids]))
    balance = await _me(world, buyer)
    ok = codes == [201, 201, 409, 409, 409] and balance == (200, 800)
    return AbuseResult("Double dépense sur 5 enchères", ok, f"codes {codes}, solde {balance}")


async def identical_bids(world: World) -> AbuseResult:
    """5 joueurs misent le même montant en même temps : une seule mise est acceptée."""
    seller = await _seller_with_cards(world, "mi-vendeur", 1)
    auction = await _sell(world, seller)
    bidders = [await world.signup(world.unique_name("mi-joueur")) for _ in range(5)]
    codes = _codes(await asyncio.gather(*[_bid(world, b, auction, 100) for b in bidders]))
    return AbuseResult(
        "5 mises identiques simultanées", codes == [201] + [409] * 4, f"codes {codes}"
    )


async def booster_race(world: World) -> AbuseResult:
    """10 ouvertures simultanées avec un seul booster en stock : une seule passe."""
    p = await world.signup(world.unique_name("bo-joueur"))
    for _ in range(9):
        assert (await world.call(p, "POST", "/boosters/open")).status_code == 200
    codes = _codes(
        await asyncio.gather(*[world.call(p, "POST", "/boosters/open") for _ in range(10)])
    )
    return AbuseResult(
        "10 ouvertures de booster pour 1 en stock", codes == [200] + [409] * 9, f"codes {codes}"
    )


async def recycle_cap(world: World) -> AbuseResult:
    """5 recyclages simultanés de 20 doublons avec un plafond de 50 : deux passent (40)."""
    p = await world.signup(world.unique_name("re-joueur"))
    mbid = world.any_track()
    world.give_cards(p, mbid, 121)
    body = {"recording_mbid": mbid, "quantity": 20}
    codes = _codes(
        await asyncio.gather(
            *[world.call(p, "POST", "/collection/recycle", json=body) for _ in range(5)]
        )
    )
    balance = await _me(world, p)
    return AbuseResult(
        "5 recyclages simultanés au-delà du plafond",
        codes == [200, 200, 409, 409, 409] and balance == (1040, 0),
        f"codes {codes}, solde {balance}",
    )


async def open_limits(world: World) -> AbuseResult:
    """8 mises en vente simultanées (5 au plus) ; 4 paris simultanés (3 au plus)."""
    seller = await _seller_with_cards(world, "li-vendeur", 8)
    body = {"recording_mbid": world.any_track(), "start_price": 100, "duration_minutes": 60}
    sales = _codes(
        await asyncio.gather(
            *[world.call(seller, "POST", "/auctions", json=body) for _ in range(8)]
        )
    )
    seller2 = await _seller_with_cards(world, "li-vendeur2", 4)
    ids = [await _sell(world, seller2) for _ in range(4)]
    gambler = await world.signup(world.unique_name("li-parieur"))
    bets = _codes(
        await asyncio.gather(
            *[
                world.call(gambler, "POST", f"/auctions/{i}/bets", json={"prediction": 150})
                for i in ids
            ]
        )
    )
    balance = await _me(world, gambler)
    ok = sales == [201] * 5 + [409] * 3 and bets == [201] * 3 + [409] and balance == (970, 30)
    return AbuseResult(
        "Limites : 5 ventes, 3 paris", ok, f"ventes {sales}, paris {bets}, {balance}"
    )


async def bet_and_bid(world: World) -> AbuseResult:
    """Parier et miser en même temps sur la même enchère : un seul des deux passe."""
    seller = await _seller_with_cards(world, "pm-vendeur", 1)
    auction = await _sell(world, seller)
    p = await world.signup(world.unique_name("pm-joueur"))
    results = await asyncio.gather(
        world.call(p, "POST", f"/auctions/{auction}/bets", json={"prediction": 150}),
        _bid(world, p, auction, 100),
    )
    codes = _codes(results)
    return AbuseResult("Parier et miser en même temps", codes == [201, 409], f"codes {codes}")


async def cancel_vs_bid(world: World) -> AbuseResult:
    """Le vendeur annule pendant qu'on mise : soit l'annulation, soit la mise, jamais les deux."""
    seller = await _seller_with_cards(world, "an-vendeur", 1)
    auction = await _sell(world, seller)
    bidder = await world.signup(world.unique_name("an-joueur"))
    cancel = world.call(seller, "POST", f"/auctions/{auction}/cancel")
    cancelled, bid = await asyncio.gather(cancel, _bid(world, bidder, auction, 100))
    balance = await _me(world, bidder)
    if cancelled.status_code == 200:
        ok = bid.status_code == 409 and balance == (1000, 0)
    else:
        ok = cancelled.status_code == 409 and bid.status_code == 201 and balance == (900, 100)
    return AbuseResult(
        "Annulation et mise simultanées",
        ok,
        f"annulation {cancelled.status_code}, mise {bid.status_code}, solde {balance}",
    )


async def authentication(world: World) -> AbuseResult:
    """Pas de jeton, faux jeton, jeton mal formé, annulation de l'enchère d'un autre."""
    seller = await _seller_with_cards(world, "au-vendeur", 1)
    auction = await _sell(world, seller)
    other = await world.signup(world.unique_name("au-autre"))
    checks = {
        "sans jeton": (await world.call(None, "GET", "/me")).status_code == 401,
        "faux jeton": (
            await world.call(None, "GET", "/me", headers={"Authorization": "Bearer faux"})
        ).status_code
        == 401,
        "schéma inconnu": (
            await world.call(None, "GET", "/me", headers={"Authorization": "Basic abc"})
        ).status_code
        == 401,
        "annulation d'autrui": (
            await world.call(other, "POST", f"/auctions/{auction}/cancel")
        ).status_code
        == 403,
        "pari du vendeur": (
            await world.call(seller, "POST", f"/auctions/{auction}/bets", json={"prediction": 150})
        ).status_code
        == 409,
    }
    failed = [k for k, v in checks.items() if not v]
    return AbuseResult("Jetons et droits", not failed, "échecs : " + (", ".join(failed) or "aucun"))


async def absurd_values(world: World) -> AbuseResult:
    """Valeurs aberrantes : le serveur doit répondre par une erreur 4xx, jamais par un 500."""
    p = await _seller_with_cards(
        world, "va-joueur", 1
    )  # il a une carte : les prix sont vraiment testés
    seller = await _seller_with_cards(world, "va-vendeur", 1)
    auction = await _sell(world, seller)
    huge = [0, -1, 10**10, 10**30]
    mbid = world.any_track()
    attempts: list[tuple[str, Awaitable]] = []
    for v in huge:
        sale = {"recording_mbid": mbid, "start_price": v, "duration_minutes": 60}
        attempts += [
            (f"prix de départ {v}", world.call(p, "POST", "/auctions", json=sale)),
            (f"mise {v}", _bid(world, p, auction, v)),
            (
                f"pronostic {v}",
                world.call(p, "POST", f"/auctions/{auction}/bets", json={"prediction": v}),
            ),
            (
                f"recyclage de {v}",
                world.call(
                    p, "POST", "/collection/recycle", json={"recording_mbid": mbid, "quantity": v}
                ),
            ),
        ]
    attempts += [
        ("offset énorme", world.call(p, "GET", "/collection", params={"offset": 10**30})),
        ("limit 0", world.call(p, "GET", "/collection", params={"limit": 0})),
        ("enchère n° énorme", world.call(p, "GET", f"/auctions/{10**30}")),
        ("enchère n° négatif", world.call(p, "GET", "/auctions/-1")),
        ("montant texte", world.call(p, "POST", f"/auctions/{auction}/bids", json={"amount": "x"})),
        ("corps vide", world.call(p, "POST", f"/auctions/{auction}/bids", content=b"")),
        (
            "titre inconnu",
            world.call(
                p,
                "POST",
                "/auctions",
                json={"recording_mbid": "inconnu", "start_price": 100, "duration_minutes": 60},
            ),
        ),
        (
            "titre avec caractère nul",
            world.call(
                p, "POST", "/collection/recycle", json={"recording_mbid": "a\u0000b", "quantity": 1}
            ),
        ),
        ("nom vide", world.call(None, "POST", "/accounts", json={"name": ""})),
        ("nom trop long", world.call(None, "POST", "/accounts", json={"name": "x" * 51})),
        (
            "nom avec caractère nul",
            world.call(None, "POST", "/accounts", json={"name": "a\u0000b"}),
        ),
    ]
    responses = await asyncio.gather(*[call for _, call in attempts])
    bad = [
        f"{label} -> {r.status_code}"
        for (label, _), r in zip(attempts, responses, strict=True)
        if not 400 <= r.status_code < 500
    ]
    return AbuseResult("Valeurs aberrantes", not bad, "; ".join(bad) or f"{len(attempts)} essais")


SCENARIOS: list[Callable[[World], Awaitable[AbuseResult]]] = [
    double_spend,
    identical_bids,
    booster_race,
    recycle_cap,
    open_limits,
    bet_and_bid,
    cancel_vs_bid,
    authentication,
    absurd_values,
]


async def run_all(world: World) -> list[AbuseResult]:
    results = []
    for scenario in SCENARIOS:
        try:
            results.append(await scenario(world))
        except Exception as exc:  # un scénario qui plante est un échec, pas un arrêt
            results.append(AbuseResult(scenario.__name__, False, f"exception {exc!r}"))
    return results
