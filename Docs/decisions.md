# Beslissingen

De keuzes die ik heb gemaakt, elk met de reden.

## Opzet

**Typer voor de CLI.** Om een mooie CLI te maken heb ik gekozen voor Typer, met één `cli.py` waarin alle commando's staan. Dat zijn dezelfde commando's die ik zelf gebruik bij het testen.

**Claude als LLM.** Ik had er nog gratis tegoed voor, en het zijn goede modellen.

**SQLite voor alles.** Ideaal voor deze casus: alles past in één bestand van ongeveer 700 MB, waarvan 400 MB aan vectoren. BM25 zit er direct in via FTS5, daar is alleen een virtuele tabel met de inverted index voor nodig. De performance van een dedicated vector database of pgvector heb ik bij deze omvang niet nodig. Geen Docker: één bestand downloaden van de release en je kunt beginnen.

## Index

**Geen extra chunking, dus een flat index.** Elke corpusrij krijgt één embedding. In een eerder project maakte ik semantic search op schonere data en direct voor mensen, zonder LLM-call ervoor of erna. Daar moest de search meteen naar de alinea wijzen waar iets stond dat erop leek. Hier leest een LLM de documenten, en de corpusrijen zijn al stukken van een bestand.

**Cohere voor de embeddings.** Eerst wilde ik OpenAI gebruiken: LLM en embeddings bij één leverancier is makkelijk. Maar Cohere en Voyage scoren op de FreshStack-leaderboard zo veel beter dat ik daarvoor koos (alpha-nDCG@10 op LangChain: Cohere Embed v5.0 Pro 0,376, voyage-4-large 0,338, OpenAI text-embedding-3-large 0,207). Voyage had wel iets gaafs: ze kunnen de chunking voor je doen en stoppen dan wat context van het hele document in elke chunk-embedding. Dat werd iets te complex, dus het is Cohere geworden, vanwege de beste score.

**Base64 eruit.** Base64-blobs worden vervangen door `[base64 removed]`. De 608 rijen die alleen uit base64 bestaan krijgen geen vector en geen BM25-regel.

## Search

**BM25 naast de embeddings.** Ik keek naar de dataset en daarin staan veel foutmeldingen en mensen met problemen. Op de FreshStack-leaderboard scoort BM25 op deze dataset ook al hoger dan de OpenAI-embeddingmodellen waar mijn oude projecten op draaiden (alpha-nDCG@10 op LangChain: BM25 0,230, text-embedding-3-small 0,213, text-embedding-3-large 0,207). Daarom vond ik de extra complexiteit het testen waard.

Met succes, al was de verandering over het algemeen klein. Sommige documenten die al hoog stonden zakten door de keywords iets, andere kwamen daardoor net in de top 10. Op de 68 dev-vragen:

| | Semantic alleen | Hybrid |
|---|---|---|
| alpha-nDCG@10 | 0,416 | 0,449 |
| Relevante documenten in de top 10, gemiddeld | 2,25 | 2,38 |

Per vraag werd het 23 keer beter, 21 keer slechter en bleef het 24 keer gelijk. Eerlijk is eerlijk: ook op dev valt dat verschil van 0,033 net binnen de ruis (95%-interval van -0,001 tot +0,070), en de gewichten zijn op diezelfde vragen gekozen. Op de testset is het verschil kleiner (0,373 tegen 0,360) en valt het ook binnen de ruis.

Bron van de leaderboard-cijfers: [leaderboard_data.json](https://fresh-stack.github.io/leaderboard_data.json) van FreshStack, gedownload op 15 november 2026.

**Drie zoekmodi: keyword, semantic en hybrid.** Hybrid scoort het best en is dus de default.

**Hybrid met score fusion: 0,7 semantic en 0,3 keyword.** Mijn eerste versie telde de rangnummers van beide lijsten even zwaar op (rank fusion 1:1). Dat scoorde op dev slechter dan semantic alleen (alpha-nDCG@10 0,390 tegen 0,416). Een rangnummer gooit weg hoe sterk een match is, en keyword telde even zwaar mee als semantic.

Versie 2 gebruikt de scores zelf. Elke lijst wordt geschaald naar 0 tot 1 en daarna opgeteld, met 0,7 voor semantic en 0,3 voor keyword. Semantic levert 200 kandidaten, keyword 50. Deze instelling komt uit 345 combinaties die ik op dev heb doorgerekend en geeft 0,449.

**Geen reranker.** Reden: lean blijven. Volgens een samenvatting van de FreshStack-paper kan reranken dense retrieval en fusion zelfs schaden. Dat heb ik niet zelf gemeten.

## Antwoord

**Versie 1 is één keer zoeken en één Claude-call.** Geen agent loop, geen tools, geen chatgeschiedenis. Reden: de opdracht beschrijft één pass, en zo is wat ik evalueer hetzelfde als wat de gebruiker krijgt. Een loop is de vervolgstap.

**Antwoord als gestructureerde JSON.** `answer` (leesbare tekst met [n]-markers), `citations` (per statement de volledige corpus-`_id`'s) en `outcome`. Onder het antwoord staat een bronnenlijst met id en GitHub-url. De statements komen met `--details`.

**Systeemprompt.** Een korte beschrijving van het corpus (geen file tree), één regel over taal en versie, code mag uit de geciteerde rijen komen, altijd Engels, geen voorbeelden. De prompt staat in een eigen bestand, zodat hij zonder Python te lezen en aan te passen is.

**Hardening in de code eromheen.** Vraag en documenten zijn data en nooit instructies. Elk antwoord krijgt controles (`violations`), zoals "geciteerd id was niet opgehaald". Lege invoer stopt vóór de betaalde call. De bronnenlijst komt uit de afgedwongen velden, niet uit de vrije tekst.

**Geen cutoff op de zoekscore vóór de LLM.** Reden: de hybrid score is per vraag geschaald en zegt niets absoluuts. Staat als beperking in `Docs/design/hardening.md`.

## Evaluatie

**Vaste split met seed 42: 68 dev en 135 test.** Zo heb ik een kleine set om mee te testen en af te stellen, en een grote voor het echte resultaat.

**Metrics: Recall@50, Coverage@20 en alpha-nDCG@10.** Dezelfde drie als de FreshStack-leaderboard, zodat mijn cijfers ernaast gelegd kunnen worden.

**Cache voor de vraagvectoren.** Tijdens het wachten op de eerste vectoren bij de retrieval-test dacht ik al: dit ga ik niet elke keer doen. Daarom worden de vectoren van alle evaluatievragen één keer opgeslagen. De antwoordrun gebruikt dezelfde cache.

**De judge: twee Claude-calls per antwoord, simpel gehouden.** Call 1 kijkt per nugget of die in het antwoord staat (full, partial of none) en of het antwoord de vraagsteller helpt (yes, partly of no). Call 2 kijkt per statement of de geciteerde documenten het dekken (supported, partly of not_supported). Het zijn twee losse calls, zodat de ene score de andere niet kleurt. Een uitgebreidere versie heb ik er weer uitgehaald: ik moet hem kunnen begrijpen en uitleggen.