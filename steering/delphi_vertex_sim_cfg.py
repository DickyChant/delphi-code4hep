import os

import FWCore.ParameterSet.Config as cms
from FWCore.Modules.modules import EmptySource
from Code4hep.G4Application.modules import G4SimProducer
from Code4hep.Generators.modules import GenProducer

process = cms.Process("DELPHIVERTEX")
process.source = EmptySource()
process.maxEvents.input = int(os.environ.get("C4H_MAX_EVENTS", "1"))
process.options.numberOfThreads = 1
process.options.numberOfStreams = 1

process.gen = GenProducer(
    generatorType=cms.string("HepMC3Generator"),
    generator=cms.InputTag("MCParticles"),
    initialSeed=cms.uint32(12345),
    Verbosity=cms.untracked.int32(0),
    PartID=cms.untracked.int32(13),
    MinPt=cms.double(10.0),
    MaxPt=cms.double(10.0),
    MinEta=cms.double(0.0),
    MaxEta=cms.double(0.0),
    MinPhi=cms.double(0.0),
    MaxPhi=cms.double(0.0),
)

process.sim = G4SimProducer(
    generator=cms.InputTag("gen", "MCParticles"),
    randomSeed=cms.uint32(67890),
    Physics=cms.PSet(type=cms.string("FTFP_BERT")),
    Detector=cms.PSet(
        gdml=cms.string(os.environ["C4H_GDML"]),
        magneticFieldTesla=cms.double(float(os.environ["C4H_FIELD_TESLA"])),
    ),
)

process.output = cms.OutputModule(
    "PodioOutputModule",
    fileName=cms.untracked.string(os.environ["C4H_OUTPUT"]),
)

process.generation_step = cms.Path(process.gen)
process.simulation_step = cms.Path(process.sim)
process.output_step = cms.EndPath(process.output)
process.schedule = cms.Schedule(
    process.generation_step,
    process.simulation_step,
    process.output_step,
)
