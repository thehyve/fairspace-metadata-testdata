#!/usr/bin/env python3
import importlib
import logging
import random
import time
import uuid
from datetime import datetime
from typing import Sequence, Dict
from urllib.parse import quote
from rdflib import Graph, Literal, RDF, URIRef
from rdflib.namespace import DCAT, Namespace, RDFS

import numpy

from fairspace_api.api import FairspaceApi

CURIE = Namespace('https://institut-curie.org/ontology#')
FS = Namespace('http://fairspace.io/ontology#')
ANALYSIS = Namespace('https://institut-curie.org/analysis#')
SUBJECT = Namespace('http://example.com/subjects#')
EVENT = Namespace('http://example.com/events#')
SAMPLE = Namespace('http://example.com/samples#')
HOMO_SAPIENS = URIRef('https://bioportal.bioontology.org/ontologies/NCBITAXON/9606')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('testdata')


def random_subset(items, count: int):
    return [items[i] for i in random.sample(range(0, len(items) - 1), count)]


class TestData:
    def __init__(self):
        self.empty_files = True
        self.subject_count = 30000
        self.event_count = 60000
        self.sample_count = 120000
        self.collection_count = 10
        self.dirs_per_collection = 100
        self.files_per_dir = 1500

        self.words = [
            'beverage',
            'test',
            'linked data',
            'fairspace',
            'philosophy',
            'music',
            'literature',
            'institute',
            'science',
            'analysis',
            'software',
            'java',
            'database',
            'new',
            'windows',
            'lab'
        ]
        # Taxonomies
        self.gender_ids: Sequence[str] = []
        self.topography_ids: Sequence[str] = []
        self.morphology_ids: Sequence[str] = []
        self.laterality_ids: Sequence[str] = []
        self.event_type_ids: Sequence[str] = []
        self.nature_ids: Sequence[str] = []
        self.analysis_ids: Sequence[str] = []

        # Generated objects and links
        self.subject_ids: Sequence[str] = []
        self.event_ids: Sequence[str] = []
        self.event_subject: Dict[str, str] = {}
        self.sample_ids: Sequence[str] = []
        self.sample_subject: Dict[str, str] = {}
        self.sample_event: Dict[str, str] = {}
        self.event_topography: Dict[str, str] = {}

        self.root = Namespace('http://localhost:8080/api/v1/webdav/')
        self.api = FairspaceApi()

    def update_taxonomies(self):
        # Update taxonomies
        data = importlib.resources.read_text('testdata', 'taxonomies.ttl')
        log.info('Updating taxonomies ...')
        self.api.upload_metadata('turtle', data)

    def update_collection_type_labels(self):
        collection_types = [
            'File',
            'Directory',
            'Collection'
        ]
        graph = Graph()
        for collection_type in collection_types:
            graph.add((FS[collection_type], RDFS.label, Literal(collection_type)))
        log.info('Updating collection type labels ...')
        self.api.upload_metadata_graph(graph)

    def query_taxonomy(self, taxonomy):
        return {result['id']['value']: result['label']['value'] for result in self.api.query_sparql(f"""
            PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX curie: <https://institut-curie.org/ontology#>
            
            SELECT ?id ?label
            WHERE {{
              ?id a curie:{taxonomy} .
              ?id rdfs:label ?label
            }}
            """)['results']['bindings']}

    def fetch_taxonomy_data(self):
        log.info('Fetching topographies ...')
        topographies = self.query_taxonomy('Topography')
        log.info('Selecting a subset of 10 topographies ...')
        self.topography_ids = random_subset(list(topographies.keys()), 10)

        log.info('Fetching morphologies ...')
        morphologies = self.query_taxonomy('Morphology')
        log.info('Selecting a subset of 10 morphologies ...')
        self.morphology_ids = random_subset(list(morphologies.keys()), 10)

        log.info('Fetching lateralities ...')
        lateralities = self.query_taxonomy('Laterality')
        self.laterality_ids = list(lateralities.keys())

        log.info('Fetching event types ...')
        event_types = self.query_taxonomy('EventType')
        self.event_type_ids = list(event_types.keys())

        log.info('Fetching sample natures ...')
        natures = self.query_taxonomy('SampleNature')
        self.nature_ids = list(natures.keys())

        log.info('Fetching analysis types ...')
        analysis_types = self.query_taxonomy('AnalysisType')
        self.analysis_ids = list(analysis_types.keys())

        log.info('Fetching genders ...')
        genders = self.query_taxonomy('Gender')
        self.gender_ids = list(genders.keys())
        self.gender_ids.sort()

    def select_gender(self):
        """
        male:female:undifferentiated = 4:4:1
        """
        assert len(self.gender_ids) == 3
        dice = random.randint(1, 9)
        if dice < 5:
            return self.gender_ids[0]
        if dice < 9:
            return self.gender_ids[1]
        return self.gender_ids[2]

    def generate_and_upload_subjects(self):
        # Add random subjects
        self.subject_ids = [str(uuid.uuid4()) for n in range(self.subject_count)]
        graph = Graph()
        for subject_id in self.subject_ids:
            subject_ref = SUBJECT[subject_id]
            graph.add((subject_ref, RDF.type, CURIE.Subject))
            graph.add((subject_ref, RDFS.label, Literal(f'Subject {subject_id}')))
            graph.add((subject_ref, CURIE.isOfGender, URIRef(self.select_gender())))
            graph.add((subject_ref, CURIE.isOfSpecies, HOMO_SAPIENS))
        log.info(f'Adding {len(self.subject_ids):,} subjects ...')
        self.api.upload_metadata_graph(graph)

    def generate_and_upload_events(self):
        # Add random tumor pathology events
        self.event_ids = [str(uuid.uuid4()) for n in range(self.event_count)]
        self.event_subject = {event_id: self.subject_ids[random.randint(0, len(self.subject_ids) - 1)]
                              for event_id in self.event_ids}
        self.event_topography = {event_id: self.topography_ids[random.randint(0, len(self.topography_ids) - 1)]
                                 for event_id in self.event_ids}
        graph = Graph()
        for event_id in self.event_ids:
            event_ref = EVENT[event_id]
            graph.add((event_ref, RDF.type, CURIE.TumorPathologyEvent))
            graph.add((event_ref, RDFS.label, Literal(f'Tumor pathology event {event_id}')))
            graph.add((event_ref, CURIE.eventSubject,
                       SUBJECT[self.event_subject[event_id]]))
            graph.add((event_ref, CURIE.topography,
                       URIRef(self.event_topography[event_id])))
            graph.add((event_ref, CURIE.tumorMorphology,
                       URIRef(self.morphology_ids[random.randint(0, len(self.morphology_ids) - 1)])))
            graph.add((event_ref, CURIE.tumorLaterality,
                       URIRef(self.laterality_ids[random.randint(0, len(self.laterality_ids) - 1)])))
            graph.add((event_ref, CURIE.eventType,
                       URIRef(self.event_type_ids[random.randint(0, len(self.event_type_ids) - 1)])))
            graph.add((event_ref, CURIE.term('ageAtDiagnosis'),
                       Literal(max(0, min(int(numpy.random.standard_normal() * 15) + 50, 120)))))
        log.info(f'Adding {len(self.event_ids):,} tumor pathology events ...')
        self.api.upload_metadata_graph(graph)

    def add_sample_diagnosis_subject_topography_fragment(self, graph: Graph, sample_id: str):
        sample_ref = SAMPLE[sample_id]
        dice = random.randint(1, 6)
        if dice < 3:
            event_id = self.event_ids[random.randint(0, len(self.event_ids) - 1)]
            subject_id = self.event_subject[event_id]
            self.sample_event[sample_id] = event_id
            self.sample_subject[sample_id] = subject_id
            graph.add((sample_ref, CURIE.subject, SUBJECT[subject_id]))
            graph.add((sample_ref, CURIE.diagnosis, EVENT[event_id]))
            graph.add((sample_ref, CURIE.topography, URIRef(self.event_topography[event_id])))
            return
        if dice < 5:
            subject_id = self.subject_ids[random.randint(0, len(self.subject_ids) - 1)]
            self.sample_subject[sample_id] = subject_id
            graph.add((sample_ref, CURIE.subject, SUBJECT[subject_id]))
            graph.add((sample_ref, CURIE.topography,
                       URIRef(self.topography_ids[random.randint(0, len(self.topography_ids) - 1)])))
            return
        graph.add((sample_ref, CURIE.topography,
                   URIRef(self.topography_ids[random.randint(0, len(self.topography_ids) - 1)])))

    def generate_and_upload_samples(self):
        # Add random samples
        self.sample_ids = [str(uuid.uuid4()) for n in range(self.sample_count)]
        graph = Graph()
        for sample_id in self.sample_ids:
            sample_ref = SAMPLE[sample_id]
            graph.add((sample_ref, RDF.type, CURIE.BiologicalSample))
            graph.add((sample_ref, RDFS.label, Literal(f'Sample {sample_id}')))
            graph.add((sample_ref, CURIE.isOfNature,
                       URIRef(self.nature_ids[random.randint(0, len(self.nature_ids) - 1)])))
            graph.add((sample_ref, CURIE.tumorCellularity,
                       Literal(max(0, min(int(numpy.random.standard_normal() * 15) + 50, 100)))))
            self.add_sample_diagnosis_subject_topography_fragment(graph, sample_id)
        log.info(f'Adding {len(self.sample_ids):,} samples ...')
        self.api.upload_metadata_graph(graph)

    def select_keywords(self) -> Sequence[str]:
        count = min(int(numpy.random.exponential(1.3)), len(self.words) - 1)
        return [self.words[i]
                for i in random.sample(range(0, len(self.words) - 1), count)]

    def select_samples(self) -> Sequence[URIRef]:
        count = min(int(numpy.random.exponential(1)), len(self.sample_ids) - 1)
        return [SAMPLE[self.sample_ids[i]]
                for i in random.sample(range(0, len(self.sample_ids) - 1), count)]

    def select_analysis_types(self) -> Sequence[URIRef]:
        count = min(int(numpy.random.exponential(.4)), len(self.analysis_ids) - 1)
        return [URIRef(self.analysis_ids[i])
                for i in random.sample(range(0, len(self.analysis_ids) - 1), count)]

    def select_subjects(self) -> Sequence[URIRef]:
        count = min(int(numpy.random.exponential(.9)), len(self.subject_ids) - 1)
        return [SUBJECT[self.subject_ids[i]]
                for i in random.sample(range(0, len(self.subject_ids) - 1), count)]

    def add_file_subject_sample_event_fragment(self, graph: Graph, ref: URIRef):
        dice = random.randint(1, 6)
        if dice == 1:
            # sample with event
            sample_id = list(self.sample_event.keys())[random.randint(0, len(self.sample_event) - 1)]
            event_id = self.sample_event[sample_id]
            subject_id = self.event_subject[event_id]
            graph.add((ref, CURIE.sample, SAMPLE[sample_id]))
            graph.add((ref, CURIE.aboutEvent, EVENT[event_id]))
            graph.add((ref, CURIE.aboutSubject, SUBJECT[subject_id]))
            return
        if dice == 2:
            # random subjects
            for subject_ref in self.select_subjects():
                graph.add((ref, CURIE.aboutSubject, subject_ref))
            return
        if dice == 3:
            # random samples
            for sample_ref in self.select_samples():
                graph.add((ref, CURIE.sample, sample_ref))
            return
        return

    def generate_and_upload_collections(self):
        log.info('Preparing workspace and collection for uploading ...')

        workspace = self.api.find_or_create_workspace('test')

        collection_name_prefix = f'collection {datetime.now().strftime("%Y-%m-%d_%H_%M")}'

        for m in range(self.collection_count):
            collection_name = f'{collection_name_prefix}-{m}'
            self.api.ensure_dir(collection_name, workspace)

            # Upload test files
            for n in range(self.dirs_per_collection):
                if n % 10 == 0:
                    time.sleep(5)

                path = f'{collection_name}/dir_{n}'
                self.api.ensure_dir(path)

                files = {f'coffee_{m}.jpg': 'coffee.jpg' for m in range(self.files_per_dir)}

                log.info(f'Adding {self.files_per_dir:,} files into {path} ...')
                if self.empty_files:
                    self.api.upload_empty_files(path, files.keys())
                else:
                    self.api.upload_files_by_path(path, files)

                # Annotate files with metadata
                graph = Graph()
                for file_name in files.keys():
                    file_id = self.root[f'{quote(path)}/{quote(file_name)}']
                    for analysis_type in self.select_analysis_types():
                        graph.add((file_id, CURIE.analysisType, analysis_type))
                    for keyword in self.select_keywords():
                        graph.add((file_id, DCAT.keyword, Literal(keyword)))
                    self.add_file_subject_sample_event_fragment(graph, file_id)
                log.info(f'Adding metadata for {len(files)} files to {path} ...')
                self.api.upload_metadata_graph(graph)

    def run(self):
        self.update_taxonomies()
        self.update_collection_type_labels()
        self.fetch_taxonomy_data()
        self.generate_and_upload_subjects()
        self.generate_and_upload_events()
        self.generate_and_upload_samples()
        self.generate_and_upload_collections()


def main():
    TestData().run()


if __name__ == '__main__':
    main()
