"""Joueurs virtuels à comportement aléatoire (graine fixe : une simulation se rejoue à l'identique).
Les probabilités ne sont pas des règles du jeu : elles décrivent seulement des profils de test."""

from dataclasses import dataclass

from tracks.config import get_rules
from tracks.simulation.world import Player, World


@dataclass(frozen=True)
class Profile:
    name: str
    open_booster: float
    recycle: float
    sell: float
    bid: float
    bet: float
    cancel: float


PROFILES = (
    Profile("collectionneur", 0.30, 0.10, 0.05, 0.30, 0.05, 0.02),
    Profile("parieur", 0.30, 0.10, 0.03, 0.08, 0.40, 0.02),
    Profile("vendeur", 0.30, 0.15, 0.20, 0.10, 0.08, 0.05),
)


class Bot:
    def __init__(self, player: Player, profile: Profile) -> None:
        self.player = player
        self.profile = profile
        self.own_auctions: list[int] = []

    async def act(self, world: World, auctions: list[dict]) -> None:
        rng, p, me = world.rng, self.profile, self.player
        if rng.random() < p.open_booster:
            await world.call(me, "POST", "/boosters/open")

        do_recycle, do_sell = rng.random() < p.recycle, rng.random() < p.sell
        if do_recycle or do_sell:
            r = await world.call(me, "GET", "/collection", params={"limit": 200})
            cards = r.json() if r.status_code == 200 else []
            doubles = [c for c in cards if c["quantity"] > 1]
            if do_recycle and doubles:
                c = rng.choice(doubles)
                body = {"recording_mbid": c["id"], "quantity": rng.randint(1, c["quantity"] - 1)}
                await world.call(me, "POST", "/collection/recycle", json=body)
            if do_sell and cards:
                body = {
                    "recording_mbid": rng.choice(cards)["id"],
                    "start_price": rng.randint(10, 120),
                    "duration_minutes": rng.choice(get_rules().auction.durations_minutes),
                }
                r = await world.call(me, "POST", "/auctions", json=body)
                if r.status_code == 201:
                    self.own_auctions.append(r.json()["id"])

        others = [a for a in auctions if a["seller_id"] != me.id]
        if others and rng.random() < p.bid:
            a = rng.choice(others)
            amount = a["min_next_bid"] + rng.randint(0, max(1, a["min_next_bid"] // 5))
            await world.call(me, "POST", f"/auctions/{a['id']}/bids", json={"amount": amount})
        if others and rng.random() < p.bet:
            a = rng.choice(others)
            guess = a["current_price"] + rng.randint(0, 2 * a["current_price"])
            await world.call(me, "POST", f"/auctions/{a['id']}/bets", json={"prediction": guess})
        if self.own_auctions and rng.random() < p.cancel:
            auction_id = self.own_auctions.pop(rng.randrange(len(self.own_auctions)))
            await world.call(me, "POST", f"/auctions/{auction_id}/cancel")
