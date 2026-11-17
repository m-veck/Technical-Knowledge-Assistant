# Eindverslag

Beste reviewer, dankjewel voor het doorlezen van deze file. Hier staat mijn eindverslag van de casus: wat ik heb gemaakt, wat de testen mij zeggen, waar ik tegenaan liep en waar ik denk dat het nog beter kan.

## 1. Wat ik heb gemaakt

Allereerst heb ik een simpele Knowledge Assistant gemaakt: één hybride retrieval, waarvan het resultaat door een LLM wordt gehaald om er een mooi antwoord van te maken. De search combineert BM25 met Cohere-embeddings over 49.505 documenten, en de beste 10 gaan naar Claude Sonnet 5.5, die antwoordt met een verwijzing naar zijn bronnen. Geen fancy features zoals history of reasoning loops, maar wie heeft dat ook nodig.

De assistent is te gebruiken via de `tka` CLI. Hiermee zet je hem op, en met het commando `ask` kun je zelf vragen stellen.

Om te kijken hoe goed het werkt heb ik evaluatiecode gemaakt, in twee onderdelen.

Het eerste onderdeel test mijn BM25 en Cohere-embeddings, met de drie getallen die FreshStack zelf gebruikt (Recall@50, Coverage@20 en alpha-nDCG@10), op 68 vragen die ik apart heb gehouden om op af te stellen. Uiteindelijk heb ik hiermee prima weights gevonden (0,7 semantic en 0,3 keyword) waarmee ik de semantic search stabieler en ook beter kon krijgen: op die 68 vragen een alpha-nDCG@10 van 0,45, tegen 0,42 voor semantic alleen.

Het tweede onderdeel is een evaluation judge die de antwoorden van de AI controleert. Zorgen dat de documenten met de nuggets (de juiste informatie) in de top 10 komen is nice, maar of de AI ook echt iets doet met die informatie is dan de vraag. Vandaar dat ik dit heb gemaakt. De judge is ook Claude, met twee calls per antwoord: staat elke nugget in het antwoord en helpt het de vraagsteller, en dekken de geciteerde documenten wat het antwoord zegt?

## 2. Resultaten

De testset van 135 vragen is één keer gedraaid, nadat alles vaststond. De 68 dev-vragen zijn de vragen waarop ik heb afgesteld. Alle details per vraag staan in de twee rapporten: [test](../reports/report-test.html) en [dev](../reports/report-dev.html).

| | Test (135 vragen) | Dev (68 vragen) |
|---|---|---|
| Nuggets met een ondersteunend document in de top 10 | 60% (257 van 431) | 68% (142 van 208) |
| Hybrid search: Recall@50, Coverage@20, alpha-nDCG@10 | 0,47, 0,72 en 0,37 | 0,52, 0,74 en 0,45 |
| Vragen beantwoord | 120 van 135 | 65 van 68 |
| Nugget-score, streng en mild | 0,32 en 0,43 | 0,30 en 0,42 |
| Behulpzaam: ja, deels, nee | 41, 68 en 11 | 22, 40 en 3 |
| Statements gedekt door hun bron | 94% (508 van 538) | 95% (290 van 304) |
| Kosten en tijd per antwoord | $0,06 en 7,8 s | $0,06 en 8,6 s |

**Het leuke**

- **De antwoorden blijven bij hun bronnen.** 94% van de geciteerde statements wordt gedekt door het document. Van de 10 die de judge "niet gedekt" noemt, komen er 9 uit twee antwoorden die een documentnummer citeerden in plaats van een id, waardoor de judge geen tekst had om tegen te controleren. Nagelezen kloppen die 9 wel.
- **Hij gokt niet.** 15 keer zei hij dat zijn documenten de vraag niet dekken. Nagelezen was dat 11 keer terecht, 2 keer verdedigbaar en 2 keer onterecht.
- **109 van de 120 antwoorden (91%) helpen de vraagsteller geheel of deels.**
- **Test en dev liggen dicht bij elkaar.** Geen enkel verschil is groter dan toeval, dus ik zie geen teken dat de afstelling op dev overfit is.
- **Goedkoop en snel:** 6 dollarcent en 8 seconden per antwoord.

**Het minder leuke**

- **De search is de bottleneck.** Bij 40% van de nuggets (174 van 431) staat er geen ondersteunend document in de top 10.
- **De antwoorden zijn niet compleet.** Gemiddeld staat een derde van wat een goed antwoord nodig heeft er volledig in (nugget-score 0,32).
- **Maar één op de drie antwoorden (41 van 120) lost het probleem helemaal op.**
- **Hybrid is op test niet aantoonbaar beter dan semantic alleen:** 0,37 tegen 0,36, en dat verschil valt binnen de ruis.

## 3. Voorbeelden

Eén goed en één slecht antwoord uit de testrun. De volledige tekst met alle oordelen staat in het [testrapport](../reports/report-test.html); zoek daar op het id van de vraag.

### Een goed antwoord (vraag 76080831)

**Vraag.** "Do LOWER results from Chroma's similarity_with_score mean HIGHER Accuracy?" De vraagsteller ziet dat de score lager is bij betere matches en vraagt of het dan een afstand is.

**Antwoord van de assistent** (volledig):

> Yes. In Chroma's `similarity_search_with_score`, the score is a distance, so a lower score means more similar. The docstring says it runs the similarity search "with distance" and that a lower score represents more similarity [1][6]. It returns each document together with its distance as a float [1]. The distance is computed by Chroma. The default metric is l2 (euclidean), which you can change with `collection_metadata={"hnsw:space": "cosine"}`; the available metrics are 'cosine', 'l2' and 'ip' [1].
>
> If you want a score where higher means more relevant, the vector store has a relevance score function. It is chosen from the collection's distance metric: cosine, l2 or ip. You can override it with `relevance_score_fn` in the Chroma constructor [1]. The documents do not show the public method that calls it, so I cannot say which method to use.
>
> The documents do not cover the Annoy page you linked.

**Oordeel.** Helpful: yes. Beide nuggets staan er volledig in, en alle 3 statements worden gedekt door hun bron. Voor beide nuggets stond een ondersteunend document in de top 10. Het antwoord kwam in 6,5 seconden.

**Waarom dit goed is.** Het beantwoordt de vraag direct, noemt bij elke zin zijn bron, en zegt eerlijk welk deel de documenten niet dekken.

### Een slecht antwoord (vraag 76170406)

**Vraag.** "Make LangChain agent ask clarifying question." Kan een LangChain-agent zelf een verduidelijkende vraag stellen als er informatie ontbreekt?

**Antwoord van de assistent** (ingekort):

> The documents do not show a built-in LangChain feature for this, but they contain related patterns.
>
> A LlamaIndex pack (not LangChain) has a QueryUnderstandingAgentWorker. [...]
>
> For LangChain, the documents show conversation memory. [...] This lets you carry on the multi-turn exchange, but the documents do not show a LangChain agent that decides on its own to ask a clarifying question. You would have to prompt for that behavior yourself, and the documents give no code for it.

**Oordeel.** Helpful: no. Geen van de 6 nuggets staat er volledig in. De oplossing uit het geaccepteerde Stack Overflow-antwoord, de `human`-tool met `initialize_agent`, ontbreekt. Wel worden alle 5 statements gedekt door hun bron. Het antwoord kwam in 7,5 seconden.

**Waarom dit slecht is.** Voor geen enkele nugget stond een ondersteunend document in de top 10. De assistent verzint niets en zegt eerlijk wat de documenten niet laten zien, maar de vraagsteller is er niet mee geholpen. De search is hier de bottleneck, en trouw aan de bron is iets anders dan behulpzaam.

## 4. Wat ik ervan vind

Ik vind het lastig. De vragen bevatten veel ruis, zoals errorberichten en code, die de search niet helpen. Ik heb één snel testje gedaan met een LLM-call die de noise eruit haalt en er nette vragen van maakt, maar die verbetering viel zwaar tegen: op dev bleef het aantal nuggets met een document in de top 10 hangen op 138 tot 142 van de 208, tegen 142 zonder die extra call.

Het jammerst vind ik wel dat er vaak documenten met het antwoord in de top 10 staan, maar dat de AI die antwoorden niet eens gebruikt. Op test stond bij 243 nuggets een ondersteunend document in de top 10, en bij 65 daarvan (27%) staat de nugget niet in het antwoord. Daar hoort wel een kanttekening bij: bij het nalezen op dev bleek het document de nugget maar in 4 van de 51 van zulke gevallen letterlijk te bevatten. Het ligt dus deels aan de AI en deels aan de labels.

Semantic search en keyword werken uit mijn testen het beste in een fusion. Ik had ook het idee om eerst een semantic search te doen en dan op de top 200 een keyword boost te gooien. Dat heb ik op dev geprobeerd en het kwam op hetzelfde uit (alpha-nDCG@10 0,44 tegen 0,45), dus op deze dataset doet dat niet veel goeds. Voor algemeen gebruik is de fusion het beste.

De meting van de LLM-judge vertrouw ik ook niet helemaal. Ik heb het idee dat er te veel kan schuiven door met de prompt te spelen en hem net wat makkelijker of moeilijker te maken. Bij het nalezen op dev was de judge inderdaad aan de strenge kant: van 15 oordelen "partial" waren er 4 tot 7 eigenlijk "full", en van de zinnen die hij aanmerkte als "zonder bron" was ongeveer één op de vijf terecht. De controle van de bronnen was wel betrouwbaar. Op zich is dat schuiven niet helemaal slecht, want daardoor zou ik hier nog wel iets mee kunnen doen, alleen is daar nu geen tijd meer voor.

## 5. Wat ik zou verbeteren

- **Een diepere reasoning loop.** Ik zou willen testen met een ReAct-loop die één of meerdere searches doet en zelf ook kan spelen met de keywords die hij uit de vraag haalt: nadenken, kijken of hij tevreden is met de informatie, en dan een antwoord maken of opnieuw gaan zoeken, maximaal 3 of 4 keer. Dat dit iets kan opleveren zag ik al in mijn testje: op de 15 slechtste dev-vragen vond een tweede search met andere woorden 16 nuggets in plaats van 7.
- **Een cut-off niveau.** Als er toch een rare search wordt afgevuurd die nergens in de buurt komt, moeten er gewoon geen resultaten terugkomen. Daarvoor heb ik de ruwe cosine similarity nodig, want de hybrid score is per vraag geschaald en zegt niets over hoe goed de beste match is.

## Tot slot

Over het algemeen ben ik heel erg blij met wat ik heb gemaakt. Na het inleveren ga ik er waarschijnlijk nog wel even mee doorspelen. Hopelijk is het voor jullie ook te volgen.
