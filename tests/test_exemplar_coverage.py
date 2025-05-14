#!/usr/bin/env python3

# Portions of this file contributed by NIST are governed by the
# following statement:
#
# This software was developed at the National Institute of Standards
# and Technology by employees of the Federal Government in the course
# of their official duties. Pursuant to Title 17 Section 105 of the
# United States Code, this software is not subject to copyright
# protection within the United States. NIST assumes no responsibility
# whatsoever for its use by other parties, and makes no guarantees,
# expressed or implied, about its quality, reliability, or any other
# characteristic.
#
# We would appreciate acknowledgement if the software is used.

import logging
from pathlib import Path
from typing import Optional, Set

from pytest import skip
from rdflib import RDF, SH, TIME, Graph, Namespace, URIRef
from rdflib.query import ResultRow

NS_KB = Namespace("http://example.org/kb/")
NS_RDF = RDF
NS_SH = SH
NS_TIME = TIME

srcdir = Path(__file__).parent
top_srcdir = srcdir.parent


def test_exemplar_coverage() -> None:
    """
    This test confirms that for each review-subject class C and property
    P in this repository's shapes graph C (/P) is used in the exemplars
    graph.
    """
    exemplar_graph = Graph()
    shapes_graph = Graph()
    tbox_graph = Graph()
    combined_graph = Graph()

    for filepath in (top_srcdir / "shapes").iterdir():
        if filepath.name.startswith("."):
            # Skip quality control test artifacts.
            continue
        if filepath.name.endswith(".ttl"):
            logging.debug("Loading shapes graph %r.", filepath)
            shapes_graph.parse(filepath)
    logging.debug("len(shapes_graph) = %d.", len(shapes_graph))

    monolithic_filepath = srcdir / "monolithic.ttl"
    tbox_graph.parse(monolithic_filepath)

    exemplar_filepath = srcdir / "exemplars.ttl"
    logging.debug("Loading exemplars graph %r.", exemplar_filepath)
    exemplar_graph.parse(exemplar_filepath)
    logging.debug("len(exemplar_graph) = %d.", len(exemplar_graph))

    combined_graph = exemplar_graph + tbox_graph

    concepts_excused: Set[URIRef] = set()
    concepts_excused_filepath = srcdir / "concepts_excused.txt"
    logging.debug("Loading excused-concepts set %r.", concepts_excused_filepath)
    with concepts_excused_filepath.open("r") as concepts_excused_fh:
        for line in concepts_excused_fh:
            cleaned_line = line.strip()
            if cleaned_line == "":
                continue
            if cleaned_line.startswith("#"):
                continue
            concepts_excused.add(URIRef(cleaned_line))
    logging.debug("len(concepts_excused) = %d.", len(concepts_excused))

    properties_mapped: Set[URIRef] = set()
    properties_with_exemplars: Set[URIRef] = set()

    result: Optional[bool]

    for n_sh_predicate_with_predicate_object in {
        NS_SH.inversePath,
        NS_SH.path,
        NS_SH.targetObjectsOf,
        NS_SH.targetSubjectsOf,
        NS_SH.zeroOrMorePath,
    }:
        for n_object in shapes_graph.objects(
            None, n_sh_predicate_with_predicate_object
        ):
            if isinstance(n_object, URIRef):
                properties_mapped.add(n_object)
    for alternative_path_result in shapes_graph.query(
        """\
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
SELECT ?nPredicate
WHERE {
  ?nShThing sh:alternativePath ?nAlternativePathList .
  ?nAlternativePathList rdf:rest*/rdf:first ?nPredicate .
  FILTER isURI(?nPredicate)
}
"""
    ):
        assert isinstance(alternative_path_result, ResultRow)
        assert isinstance(alternative_path_result[0], URIRef)
        properties_mapped.add(alternative_path_result[0])

    property_query = """\
ASK {
  ?nIndividual1 ?nUsedProperty ?nIndividual2 .
  ?nUsedProperty rdfs:subPropertyOf* ?nProperty .
}
"""
    for property_mapped in sorted(properties_mapped):
        result = None
        for property_result in combined_graph.query(
            property_query, initBindings={"nProperty": property_mapped}
        ):
            assert isinstance(property_result, bool)
            result = property_result
        if result is True:
            properties_with_exemplars.add(property_mapped)

    if properties_mapped > (properties_with_exemplars | concepts_excused):
        logging.info("These mapped properties have no exemplar instances:")
        undemonstrated_properties = (
            properties_mapped - properties_with_exemplars - concepts_excused
        )
        for undemonstrated_property in sorted(undemonstrated_properties):
            logging.info("* %s", str(undemonstrated_property))

    classes_mapped: Set[URIRef] = set()
    classes_with_exemplars: Set[URIRef] = set()

    for n_object in shapes_graph.objects(None, NS_SH.targetClass):
        assert isinstance(n_object, URIRef)
        classes_mapped.add(n_object)

    class_query = """\
ASK {
  ?nIndividual a/rdfs:subClassOf* ?nClass .
}
"""
    for class_mapped in sorted(classes_mapped):
        result = None
        for class_result in combined_graph.query(
            class_query, initBindings={"nClass": class_mapped}
        ):
            assert isinstance(class_result, bool)
            result = class_result
        if result is True:
            classes_with_exemplars.add(class_mapped)
        else:
            logging.debug("class_mapped = %r.", class_mapped)
            logging.debug("result = %r.", result)

    if classes_mapped > (classes_with_exemplars | concepts_excused):
        logging.info("These mapped classes have no exemplar instances:")
        undemonstrated_classes = (
            classes_mapped - classes_with_exemplars - concepts_excused
        )
        for undemonstrated_class in sorted(undemonstrated_classes):
            logging.info("* %s", str(undemonstrated_class))

    assert properties_mapped <= (
        properties_with_exemplars | concepts_excused
    ) and classes_mapped <= (classes_with_exemplars | concepts_excused)


def test_temporal_entity_to_instant() -> None:
    skip("TODO")
    expected: set[URIRef] = {
        NS_KB["TemporalEntity-906144d4-4663-4eb0-84f0-cdb780cef154"],
        NS_KB["Interval-3137182b-f4a2-46aa-983b-092aeb0aa56e"],
    }
    computed: set[URIRef] = set()

    graph = Graph()
    # TODO - Load.

    for n_subject in graph.subjects(NS_RDF.type, NS_TIME.Instant):
        assert isinstance(n_subject, URIRef)
        computed.add(n_subject)

    assert expected <= computed


def test_temporal_entity_to_proper_interval() -> None:
    """\
The below exemplar nodes each tie two `time:Instant`s, via the noted predicate.

| Temporal entity or Interval     | `time:hasBeginning`      | `time:inside`            | `time:inside` (2nd)      | `time:hasEnd`            |
| ---                             | ---                      | ---                      | ---                      | ---                      |
| `kb:TemporalEntity-00947113...` | `kb:Instant-0180e20a...` |                          |                          | `kb:Instant-02f01c68...` |
| `kb:Interval-119f05f1...`       | `kb:Instant-128fc0de...` | `kb:Instant-130657a0...` |                          |                          |
| `kb:Interval-2377e0a2...`       | `kb:Instant-25b30b38...` |                          |                          | `kb:Instant-264e96c9...` |
| `kb:Interval-33e90e08...`       |                          | `kb:Instant-38a01481...` | `kb:Instant-3aea3fe6...` |                          |
| `kb:Interval-422c1878...`       |                          |                          | `kb:Instant-435e90ab...` | `kb:Instant-450226bc...` |
"""
    skip("TODO")
    expected: set[URIRef] = {
        NS_KB["TemporalEntity-00947113-902d-4550-9c2c-f6175b31ef19"],
        NS_KB["Interval-119f05f1-8049-4556-86c4-c7cabcfa7fbf"],
        NS_KB["Interval-2377e0a2-a983-44d6-b5f8-a2a4538d6819"],
        NS_KB["Interval-33e90e08-7045-4369-88cd-68e96b96967c"],
        NS_KB["Interval-422c1878-dd0b-42b7-8975-42b28106a917"],
    }
    computed: set[URIRef] = set()

    graph = Graph()
    # TODO - Load.

    for n_subject in graph.subjects(NS_RDF.type, NS_TIME.ProperInterval):
        assert isinstance(n_subject, URIRef)
        computed.add(n_subject)

    assert expected <= computed
