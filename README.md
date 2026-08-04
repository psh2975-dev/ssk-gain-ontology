# SSK-GAIN: A Cross-Domain Ontology and Entity Catalogue for Semiconductor Supply Chain Geopolitics

An OWL 2 ontology in four modules with SHACL shapes, an instantiated and
machine-validated entity catalogue, and the validation toolkit that reproduces
every check reported in the accompanying article.

**Namespaces** (persistent identifiers). Registration with w3id.org was requested in
[perma-id/w3id.org#6470](https://github.com/perma-id/w3id.org/pull/6470); that pull request
records the current status. Once it is merged the IRIs below dereference to the files in
this repository, and until then they name the vocabulary without resolving.

| Target | IRI |
|---|---|
| core module | `https://w3id.org/ssk-gain/ontology/core#` |
| international relations module | `https://w3id.org/ssk-gain/ontology/intl#` |
| supply chain module | `https://w3id.org/ssk-gain/ontology/gvc#` |
| cross-domain bridge module | `https://w3id.org/ssk-gain/ontology/bridge#` |
| SHACL shapes | `https://w3id.org/ssk-gain/ontology/shapes#` |
| knowledge graph instances | `https://w3id.org/ssk-gain/kg/` |

**Archived release**: https://doi.org/10.5281/zenodo.21715914 (concept DOI resolves to the latest version)

The four modules ship as separate documents, so a consumer can retrieve
`intl.ttl` alone and follow its `owl:imports` rather than taking the whole
vocabulary; `ontology.ttl` is the merged export for consumers who want one file.

## Contents

```

verify_all.py                    runs every check available in this deposit
requirements.txt                 pinned versions used to produce these artefacts

system/ontology/ontology.ttl     merged ontology (all four modules)
system/ontology/{core,intl,gvc,bridge}.ttl   the four module documents
system/ontology/shapes.ttl       SHACL constraint shapes
system/ontology/*.py             generation, validation, metrics, traceability and
                                 OntoClean meta-property audit

system/kg/*.py                   materialisation, competency-question queries, reuse demo
system/kg/out/pilot_kg_deposit.ttl    deposited pilot graph (21,561 triples)
system/kg/out/cq_query_results.json   competency question query results
system/kg/out/materialize_report.json materialisation report (counts, SHACL verdict)
system/kg/out/reuse_demo_report.json  third-party vocabulary reuse demonstration
system/kg/out/ontoclean_audit.json    meta-property declaration and constraint check
system/kg/out/shacl_deposit.txt       SHACL validation output for the deposited graph

system/data/*.py                 repair scripts for the curated input
system/data/curated/             NOT INCLUDED: source records excluded by licence
                                 (UN Comtrade, ETO); see Reproduction below

docs/ADR-001_ontology_scope.md   scope decision record
```

## Measured figures (regenerate with the scripts below)

| Item | Value |
|---|---:|
| Named classes / object properties / datatype properties | 32 / 51 / 41 |
| `owl:disjointWith` pairs (six upper types, pairwise) | 15 |
| Deposited graph triples | 21,561 |
| Competency questions answered by live query | 8 of 17 (4 full, 4 partial) |
| SHACL conformance (deposited graph) | conforms, 0 violations |

## Reproduce

Requires Python 3.11+ with `rdflib`, `owlrl`, `pyshacl`; the exact versions
used to produce these artefacts are pinned in `requirements.txt`
(`pip install -r requirements.txt`). The ontology and shape documents
regenerate byte-deterministically: `build_ontology.py` and `build_shapes.py`
run twice yield identical files, so those artefacts can be checked by hash.
The graph and query outputs depend on the excluded source records and so
cannot be regenerated from this deposit alone. The layout mirrors the
working tree, so the scripts run unmodified from their own directories.

Run everything at once and get a summary table:

```
python verify_all.py
```

Or run the steps individually. These run entirely from this deposit:

```
cd system/ontology
python build_ontology.py     # regenerate ontology.ttl deterministically
python build_shapes.py       # regenerate shapes.ttl
python validate.py           # the eleven checks: OWL RL consistency and
                             # its non-vacuity by injected disjointness violation;
                             # the role-typing contract, catching a policy-organisation
                             # confusion while admitting a legitimate dual role;
                             # the identity axiom, same identifier inferring sameness
                             # and different identifiers not; SHACL on a conformant
                             # sample and on a violating one, with per-relation range
                             # probes and cross-node merge-conflict detection
python ontology_metrics.py   # structural metrics (32/51/41, depth, ratio)
python traceability_audit.py # vocabulary-to-competency-question mapping (90/34/0)

cd ../kg
python reuse_demo.py         # third-party reuse of the intl module alone
```

Requires source data this deposit cannot redistribute:

```
python materialize_pilot_kg.py  # needs system/data/curated/*.json, which include
                                # ETO (CC-BY-NC-4.0) and UN Comtrade records
python run_cq_queries.py        # needs out/pilot_kg_demo.ttl, built from UN Comtrade
```

```
python system/data/repair_country_codes.py   # country-code canonicalisation repair
python system/data/repair_curated_types.py   # action-vs-target typing repair
```

The two repair scripts document the deterministic repairs applied to the source
catalogue; without the excluded source files they print a notice and exit.
Obtain those sources under their own terms, implement the documented collection and normalisation stage, and the released stages rebuild both
graphs. The results these scripts produced for the article are included as
`system/kg/out/cq_query_results.json`, `materialize_report.json` and
`shacl_deposit.txt`, so their reported values remain inspectable here.

## Scope of the deposit

Records from sources whose licences do not permit redistribution are excluded:
the ETO Advanced Semiconductor dataset (CC-BY-NC-4.0) and UN Comtrade records
(United Nations copyright; re-dissemination requires UNSD consent). The schema
and the field mappings are published here together with the materialisation and validation stages, so users who obtain those sources themselves can rebuild the excluded records by implementing the documented collection and normalisation stage against the released
pipeline. Bilateral trade records in the deposit derive from BACI (CEPII) under
the Etalab Open Licence 2.0.

## Languages

Ontology labels, term definitions (`rdfs:comment`), SHACL validation messages
and the validation harness's console verdicts are in English, with Korean
kept alongside via RDF language tags (`@en` and `@ko`). Implementation
comments inside the Python scripts, and the scope decision record under
`docs/`, are written in Korean; the decision record carries an English
summary at its head.

## Licence

Ontology, shapes, curated data and documentation: CC-BY-4.0.
Scripts: MIT.
Third-party source data retain their own licences as stated above.

## Funding

National Research Foundation of Korea (NRF-2024S1A3A2A07046144).
