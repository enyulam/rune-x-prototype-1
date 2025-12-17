ZHICONG TECHNOLOGY

PROJECT RUNE-X

 INTERPRETING THE PAST. EMPOWERING THE FUTURE.

LAM EN YU, NATHAN LY, NATHANIEL NEO, STEPHEN GOH,  WONG GUO YAO

PROJECT RUNE-X

Table of Contents

1. Executive Summary ............................................................................................... 3

2. Background & Rationale ......................................................................................... 5

3. Problem Definition .................................................................................................. 8

3.1 Technical Challenges: Ancient and Historical Scripts Resist Standard OCR .... 8

3.2 Operational Bottlenecks: Manual Transcription and the Human Expert Shortage
................................................................................................................................ 9

3.3 Market & Opportunity Gap: Demand Exists — Tools Are Missing ................... 10

3.4 Summary of Problem Definition ...................................................................... 11

4. Vision & Scope of Rune-X .................................................................................... 12

5. Technical Architecture Overview ........................................................................... 15

6. Deep Technical Architecture ................................................................................. 17

6.1 Glyph Tokenisation Engine (GTE) ................................................................... 17

6.2 Semantic Transformer Model (STM) ............................................................... 18

6.3 Generative Reconstruction Module (GRM) ..................................................... 19

6.4 Dataset Pipeline .............................................................................................. 20

6.5 System Infrastructure ...................................................................................... 20

6.6 Benchmarking and Evaluation (Planned) ........................................................ 21

7. Product Architecture & UX Flow ........................................................................... 22

8. Market & Customer Analysis ................................................................................ 25

9. Competitive Landscape ........................................................................................ 28

9.1 Existing OCR & Historical Document Platforms .............................................. 28

9.2 Script-Specific Machine Learning Research & Prototypes .............................. 28

9.3 Key Limitations and Gaps in Existing Solutions .............................................. 29

9.4 Rune-X’s Comparative Advantage .................................................................. 30

1 | P a g e

PROJECT RUNE-X

10. Business Model & Revenue Strategy ................................................................. 32

10.1 Core Monetization Models ............................................................................ 32

10.2 Alignment with Heritage Sector Economics & Institutional Needs................. 33

10.3 Value Proposition & Customer Segments ..................................................... 33

10.4 Competitive & Market Strategy ..................................................................... 34

10.5 Risk Management & Revenue Safeguards ................................................... 35

11. Implementation Roadmap .................................................................................. 36

11.1 Phase I: Foundational Development (Months 1–6) ....................................... 36

11.2 Phase II: Integration and Institutional Pilots (Months 7–14) .......................... 37

11.3 Phase III: Scaling, Optimisation, and Deployment (Months 15–30) .............. 37

12. Risk Assessment & Mitigation Strategy .............................................................. 39

12.1 Technical Risks ............................................................................................. 39

12.2 Data Availability and Quality Risks ................................................................ 39

12.3 Institutional and Adoption Risks .................................................................... 40

12.4 Ethical, Cultural, and Governance Risks ...................................................... 41

12.5 Long-Term Sustainability Risks ..................................................................... 41

13. Financial Outlook and Sustainability Analysis .................................................... 42

13.1 Revenue Structure and Forecast Logic ........................................................ 42

13.2 Cost Structure and Operational Expenditure Dynamics ................................ 42

13.3 Break-Even Considerations and Growth Horizon ......................................... 43

13.4 Long-Term Sustainability and Innovation Pipeline ........................................ 44

14. Conclusion ......................................................................................................... 45

References ............................................................................................................... 46

2 | P a g e

PROJECT RUNE-X

1. Executive Summary

Rune-X  is  an  advanced,  multimodal  artificial-intelligence  platform  designed  to

automate  the  interpretation  of  ancient  scripts  and  inscriptions.  It  addresses  a  long-

standing  and  widely  documented  gap  in  global  cultural-heritage  workflows:  while

museums, archives, and research institutions have digitised millions of artefacts, the

vast  majority  of  these  digital  assets  remain  untranscribed,  uncontextualised,  and

semantically inaccessible. Conventional OCR systems fail on ancient scripts due to

irregular  glyph  structures,  erosion,  material  degradation,  and  extreme  stylistic

variability,  creating  a  persistent  bottleneck  that  only  specialised  human  experts  can

overcome.  Rune-X  directly  responds  to  this  global  need  by  transforming  digitised

inscriptions into structured, machine-readable knowledge.

Rooted  in  recent  advances  in  multimodal  learning,  transformer  architectures,  and

generative modelling, Rune-X integrates three technically robust components: a Glyph

Tokenisation  Engine  capable  of  isolating  incomplete  or  irregular  characters;  a

Semantic  Transformer  Model  that  infers  phonetic,  semantic,  or  structural  meaning

from  visual  and  contextual  cues;  and  a  Generative  Reconstruction  Module  that

restores  damaged  glyphs  using  evidence-driven  synthesis  techniques.  Together,

these  subsystems  form  an  end-to-end  pipeline  capable  of  handling  real-world

archaeological  conditions  across  multiple  scripts,  imaging  modalities,  and  historical

periods. The platform is engineered for institutional workflows, supporting metadata

preservation, provenance tracking, version control, TEI-XML or JSON-LD export, and

integration with digital-asset management systems.

The market landscape underscores Rune-X’s relevance. Cultural-heritage institutions

worldwide are expanding their digitisation programmes, yet they lack scalable tools for

interpretation.  The  decipherment  of  carbonised  Herculaneum  scrolls  through  AI-

assisted  analysis,  widely  reported  in  2024,  has  demonstrated  the  viability  and

scholarly value of computational methods in heritage contexts. Rune-X capitalises on

this momentum by offering a comprehensive, production-ready platform rather than a

single-script  or  single-task  prototype.  Its  hybrid  business  model  —  combining

subscription access, consumption-based billing, and premium services — aligns with

institutional budget structures and the operational realities of heritage digitisation.

3 | P a g e

PROJECT RUNE-X

The  implementation  roadmap  outlines  a  clear  and  feasible  progression  from

foundational  development  to  institutional  pilot  partnerships  and,  ultimately,  scaled

deployment. Risks related to data variability, institutional adoption, cultural governance,

and  long-term  technical  maintenance  are  addressed  through  domain  adaptation

strategies,  explainable  outputs,  governance-appropriate  deployment  options,  and

sustainable research and infrastructure planning.

Rune-X represents a technologically rigorous, culturally informed, and institutionally

viable solution to one of the most pressing challenges in digital heritage: transforming

digital preservation  into  digital understanding. By enabling  scalable  interpretation  of

humanity’s  oldest  writing  systems,  Rune-X  strengthens  scholarship,  accelerates

conservation, and broadens public access to cultural knowledge. It stands poised to

become  a  foundational  component  of  the  next  generation  of  cultural-heritage

infrastructure.

4 | P a g e

PROJECT RUNE-X

2. Background & Rationale

Human civilization is built upon written language. From oracle bone inscriptions and

bronze vessel scripts in ancient China to hieroglyphs, runes, cuneiform, and classical

Greek,  ancient  writing  systems  form  the  primary  evidence  base  for  understanding

political history, cultural transmission, scientific development, and religious evolution.

Over the past two decades, governments, museums, libraries, and cultural institutions

worldwide  have  invested  heavily  in  the  digitisation  of  manuscripts,  inscriptions,

artefacts, and historical documents. UNESCO reports that digitisation is increasingly

recognised as a critical method for preserving cultural heritage, particularly in regions

facing conflict, natural degradation, or infrastructural instability (UNESCO, 2024). Yet

despite  rapid  growth  in  scanning  technologies  and  digital  archiving  initiatives,  the

majority of digitised material remains nothing more than static images. While digital

preservation secures the visual appearance of endangered texts, it does not provide

access to their meaning. Without interpretation, translation, transcription, or semantic

extraction, these digitised items remain academically underutilised and inaccessible

to historians, linguists, educators, and the public.

The gap between digitisation and interpretation is severe. Traditional optical character

recognition  (OCR)  systems  have  made  impressive  strides  on  modern  printed

languages, but they perform poorly on ancient and historical writing systems. Ancient

scripts  such  as  oracle  bone  inscriptions,  hieroglyphic  systems,  runes,  cuneiform

tablets, and early handwritten manuscripts display irregular shapes, stylistic variations,

non-standardised  glyph  structures,  erosion,  missing  strokes,  and  linguistic  features

that  do  not  conform  to  modern  OCR  assumptions. A  review  of AI  approaches  for

ancient scripts concludes that contemporary OCR tools consistently fail when faced

with  the  variability  and  degradation  characteristic  of  archaeological  inscriptions.

Similarly,  a  2025  survey  of  ancient-script  image  recognition  describes  how  existing

methods  struggle  with  imbalanced  data  distributions,  degradation  (such  as  erosion,

scratches, breaks), and the enormous variety of symbol shapes across scripts such

as  Egyptian  hieroglyphics,  oracle-bone  inscriptions,  ancient  Greek  inscriptions,  and

more (Diao, et al., 2025).

Efforts  to  apply  conventional  OCR  (or  even  CNN-based  text  recognition)  to  such

scripts  have  frequently  yielded  unsatisfactory  results;  for  many  ancient  inscriptions,

5 | P a g e

PROJECT RUNE-X

character  segmentation  fails,  recognition  accuracy  is  low,  and  errors  abound,

especially  when  inscriptions  are  weathered  or  damaged,  or  when  glyphs  diverge

markedly from modern typographic conventions (Anitha Julian, 2023).

Meanwhile,  the  scale  of  digitised  heritage  is  expanding  rapidly,  yet  the  capacity  to

transform  raw  images  into  usable,  annotated,  searchable  content  remains  severely

limited.  The  traditional  workflow  (manual  transcription,  expert-driven  philological

analysis,  translation,  annotation)  depends  heavily  on  specialised  philologists,

epigraphers, and paleo-linguists — experts who are in limited global supply. Given the

scale and diversity of global heritage, this presents a significant bottleneck: even when

digital archives exist, meaningful interpretation may take years or decades, and large

portions may never be processed.

In recent years, however, advances in artificial intelligence (AI), computer vision, and

machine  learning  (ML)  have  begun  to  close  this  gap.  Several  cutting-edge  efforts

demonstrate  that  AI  can  do  what  was  previously  thought  too  difficult:  interpreting

charred or heavily degraded manuscripts, reconstructing missing or damaged glyphs,

and  making  inscriptions  legible  without  physical  unwrapping. A  particularly  striking

example  is  the  recent  breakthrough  on  the  so-called  Herculaneum  scrolls  —

carbonized ancient Roman papyri buried by the eruption of Mount Vesuvius in 79 A.D.

In 2024, researchers using high-resolution CT scans combined with machine-learning

algorithms  succeeded  in  virtually  “unwrapping”  one  of  the  charred  scrolls  and

recovering  Greek  text,  a  feat  long  considered  impossible  (Marchant,  How  AI  is

unlocking  ancient  texts  —  and  could  rewrite  history,  2024)  (Marchant, AI  Unravels

Ancient Roman Scroll Charred By Volcano, 2024).

Beyond single successes, academic surveys show growing momentum for AI-assisted

epigraphy and ancient-language processing. A 2023 survey under “Machine Learning

for Ancient Languages” outlines how modern ML techniques (including self-supervised

learning,  multimodal  modelling,  contextual  inference)  are  increasingly  applied  to

historical scripts across diverse languages and periods (Thea Sommerschield, et al.,

2023). These developments suggest that fundamental barriers  (lack of ground-truth

data, damage, script diversity) can be overcome with carefully designed architectures,

data augmentation, and noise-robust learning.

6 | P a g e

PROJECT RUNE-X

It is within this evolving technical, cultural and academic landscape that we propose

Rune-X:  a  purpose-built,  multimodal  AI  engine

for

the  semantic  analysis,

reconstruction, and decoding of ancient scripts and inscriptions. Unlike traditional OCR

or manual annotation workflows, Rune-X intends to operate at multiple levels: glyph-

level  tokenization,  semantic  inference,  generative  reconstruction  of  degraded  or

incomplete glyphs, and output of machine-readable representations (text, metadata,

structural annotations). This architecture is designed to turn static digital images into

interpretable, searchable, and structured heritage data  — unlocking the latent value

of digital archives.

Rune-X’s rationale is threefold. First, cultural and heritage preservation: many ancient

texts and inscriptions are at risk of being permanently lost due to decay, deterioration,

or catastrophic  events.  Digital images  alone are  insufficient;  semantic  interpretation

ensures their meaning survives. Second, academic and research utility: by providing

scalable, automated support for script recognition and reconstruction, Rune-X enables

philologists,  historians,  archaeologists,  and

linguists

to  conduct

large-scale

comparative  studies,  cross-era  analyses,  and  data-driven  research,  accelerating

discoveries that manual transcription could never match in speed or breadth. Third,

strategic  and  technical  leverage:  by  building  on  advanced  AI  research,  modern

imaging methods, and data-driven modelling, Rune-X occupies a unique technological

position — few existing tools or institutions combine glyph-level modelling, semantic

inference,  generative  reconstruction,  and  multilingual  ancient-script  support  in  one

unified platform.

In short, the convergence of large, digitised heritage archives, breakthroughs in AI and

imaging, and the urgent need for scalable interpretation creates a unique window of

opportunity.  Rune-X  is  conceived  precisely  for  this  moment:  to  bridge  the  divide

between digital preservation and digital understanding, transforming humanity’s static

archives  of  the  past  into  living,  accessible  knowledge  for  present  and  future

generations.

7 | P a g e

PROJECT RUNE-X

3. Problem Definition

Humanity  today  faces  a  critical bottleneck  between  the  growing  volume  of  digitised

heritage content and the ability to interpret, annotate, and make this content usable.

The  problems  fall  into  three  interlocking  categories:  technical  limitations  of  existing

recognition  methods,  operational  bottlenecks

in  manual

transcription  and

interpretation,  and  market/opportunity  gaps  that  make  large-scale  development  of

interpretative tools both necessary and economically viable.

3.1 Technical Challenges: Ancient and Historical Scripts Resist

Standard OCR

Modern OCR and document-recognition technologies are optimised for contemporary

printed  text  or  fairly  regular handwritten  scripts. They  struggle,  and  often  fail,  when

faced  with  the  complexity  and  variability  of  ancient,  historical,  or  archaeological

inscriptions. Several inter-linked factors contribute to this difficulty:

1.  Visual degradation, damage, and non-uniformity.

Many  inscriptions  and  manuscripts  have  suffered  erosion,  fading,  cracking,

staining,  or physical  damage over centuries. Ancient  scribes  and  carvers did

not follow modern font or printing standards — letterforms vary by time, region,

material, writing tool, and even individual scribe. As a result, glyph shapes are

irregular, context- and style-dependent, and frequently incomplete. According

to  a  recent  survey  of  “ancient-script  image  recognition  and  processing,”

conventional  OCR  methods  and  even  classic  deep-learning–based  systems

consistently underperform on such data (Diao, et al., 2025).

2.  Sparse or imbalanced data resources.

For  many  ancient  scripts  (oracle  bones,  cuneiform,  Old  Aramaic,  ancient

manuscripts),  there  simply are  not  enough high-quality,  labelled  examples  to

train supervised OCR or recognition models. This scarcity inhibits the formation

of  robust  models  capable  of  generalising  across  variant  letterforms,  damage

patterns,  or  material  differences.  A  2023  study  on  Old  Aramaic  inscriptions

developed  a  synthetic-data  pipeline  precisely  to  overcome  this  challenge,

highlighting  that  real-world  datasets  remain  insufficient  for  deep-learning

8 | P a g e

PROJECT RUNE-X

approaches without augmentation (Aioanei A. C., Hunziker-Rodewald, Klein, &

Michels, 2023).

3.  Semantic (not just shape) complexity and ambiguity.

Even if shapes are detected correctly, transforming glyphs into meaningful text

(with semantics, context, historical conventions, and plausible reconstructions)

requires  more  than  pattern  recognition.  Traditional  OCR  typically  outputs

surface-level text; it cannot infer missing strokes, damaged lines, or contextual

meaning. For many archaeological texts, this limitation makes OCR output, if

produced, of little interpretative value.

Because of these limitations, a significant portion of digitised heritage remains “stuck”

at the image level: preserved visually but not interpretable, searchable, or usable for

scholarship or public dissemination.

3.2  Operational  Bottlenecks:  Manual  Transcription  and  the

Human Expert Shortage

Even  when  institutions  commission  manual transcription, decoding,  translation,  and

semantic annotation of ancient texts, the process is extremely slow, labour-intensive,

and relies heavily on specialist expertise (philologists, epigraphers, palaeographers,

or historians with narrow domain knowledge). Several problems emerge:

•  The number of qualified experts globally is limited. Ancient scripts span many

languages,  writing  systems,  and  historical  periods;  experts  often  specialise

narrowly, limiting throughput.

•  The backlog of digitised yet untranslated or unanalysed documents is vast. With

increasing digitisation, archives are growing faster than scholars can process

them.

•  Manual  methods  are  cost-prohibitive.  Time,  attention,  and  scholarly  labour

required  per  document  (especially  damaged  or  fragmented  texts)  are  high;

many institutions lack resources to commit large-scale annotation efforts.

Consequently, even well-digitised archives remain under-utilised: billions of characters’

worth  of  inscriptions  may  be  effectively  inaccessible;  image  files  sitting  unread,

unusable for research or public access.

9 | P a g e

PROJECT RUNE-X

This  operational  friction  strongly  constrains  cultural  heritage  research,  delays

discoveries,  limits  educational  access,  and  risks  permanent  knowledge  loss  if

materials degrade further or get damaged.

3.3  Market  &  Opportunity  Gap:  Demand  Exists  —  Tools  Are

Missing

At  the  same  time,  recent  technological  progress,  emerging  academic  interest,  and

institutional needs point to a growing and under-served market demand:

•  The success of cutting-edge projects shows that AI can now tackle previously

intractable  challenges.  For  instance,  in  2024  researchers  used  machine

learning and advanced imaging to successfully reveal text from a 2,000-year-

old  scroll  charred  in  the  eruption  of  Mount  Vesuvius  (the  so-called  Vesuvius

Challenge). The team digitally “unrolled” the scroll using X-ray scans and AI-

driven ink detection, yielding legible ancient Greek text (National Endowment

for the Humanities (NEH), 2024) (Henshall, 2024).

•  A  large-scale  study  on  ancient-script  image  recognition  published  in  2025

demonstrates that the problems of damage, material variety, and script diversity,

long  considered  fundamental  obstacles,  can  be  addressed  via  carefully

designed deep-learning and computer-vision pipelines. This validates the core

technical feasibility of a system like Rune-X (Diao, et al., 2025).

•  For  certain  ancient-script  domains  (such  as  Old Aramaic)  researchers  have

shown that synthetic data generation, combined with deep neural networks, can

successfully  classify  degraded  inscriptions  despite  sparse  real-world  training

data (Aioanei A. C., Hunziker-Rodewald, Klein, & Michels, 2023).

These successes indicate that the technical foundation is now strong enough to build

a  production-grade,  general-purpose  platform  for  ancient  script  decoding.  Yet  no

widely  adopted,  full-stack  system  currently  exists  that  combines  optical-level  image

processing,  semantic  inference,  generative  reconstruction,  metadata  output,  and

support  for  multiple  scripts.  This  gap  —  between  proof-of-concept  research  and

deployable infrastructure — represents a real market and academic opportunity.

10 | P a g e

PROJECT RUNE-X

In  summary,  the  world  faces  a  three-fold  failure:  digitisation  without  interpretation;

manual  methods  with  limited  scale;  and  a  lack  of  robust  tools  despite  increasing

demand.  Rune-X  is  designed  to  remediate  precisely  this  triad  of  failure,  offering  a

scalable, AI-driven, and extensible solution that addresses technical, operational, and

market needs simultaneously.

3.4 Summary of Problem Definition

The core problem is that digitised heritage content generally remains inert and under-

utilised. Ancient  and  historical  scripts  resist  standard  OCR,  requiring  new  technical

methods. Meanwhile, manual transcription is too slow and resource-intensive to keep

up with accelerating digitisation. At the same time, there is strong emerging demand

from  academia,  cultural institutions,  and  heritage  preservation  projects, for scalable

tools  to  transform  digital  images  into  meaningful,  structured  knowledge.  Without  a

unified, AI-powered  solution,  a  large  proportion  of  humanity’s  written  heritage  risks

remaining opaque, inaccessible, or lost.

11 | P a g e

PROJECT RUNE-X

4. Vision & Scope of Rune-X

The vision of Rune-X is to create the world’s first general-purpose, production-grade

multimodal  AI  engine  capable  of  interpreting,  reconstructing,  and  semantically

understanding  ancient  scripts  at  scale.  While  recent  advances  in  machine  learning

have demonstrated that AI can decode charred scrolls, classify ancient inscriptions,

and reconstruct missing glyphs, these capabilities remain scattered across specialised

research projects and have not been translated into an integrated system deployable

by  museums,  cultural  institutions,  universities,  or  government  agencies.  Rune-X

positions  itself  at  this  frontier:  a  single  platform  that  unifies  glyph  tokenisation,

semantic  inference,  generative  reconstruction,  and  cross-script  extensibility  into  a

cohesive, scalable framework.

Fundamentally, Rune-X embodies the belief that digitised heritage should not remain

passive imagery. As digitisation accelerates, driven by cultural-preservation policies,

national  archives  programmes,  and  UNESCO-aligned

initiatives,

institutions

increasingly  recognise  that  preservation  must  extend  beyond  images  to  accessible

knowledge. Digital heritage can only fulfil its purpose when users can search, interpret,

compare,  and  analyse  the  content  it  contains.  Rune-X  was  conceived  precisely  to

bridge this gap by making ancient, damaged, or understudied inscriptions machine-

readable, human-interpretable, and computationally searchable.

Technically, Rune-X aims to serve as a multimodal cognitive layer sitting atop existing

digitisation  pipelines.  The  system  ingests  photographic,  scanned,  or  multispectral

images  of  inscriptions  and  processes  them  through  three  tightly  integrated  AI

components:  a  glyph-tokenisation  engine  that  segments  and  encodes  ancient

characters; a transformer-based semantic model designed to infer meaning, phonetic

values,  and  linguistic  structure;  and  a  reconstruction  engine  capable  of  repairing

eroded  or  incomplete  glyphs.  This  approach  builds  on  the  trajectory  of  current

research in ancient-script processing, including multimodal and multitask models that

restore damaged writing (Duan, Wang, & Su, 2024) and on recent advances that apply

neural models to highly degraded materials (Kuta, 2025).

The scope of Rune-X is intentionally broad yet phased. Initial development will focus

on  scripts  with  established  datasets  and  demonstrated  machine-learning  feasibility.

For  example,  oracle-bone  inscriptions,  among  the  oldest  Chinese  writing  systems,

12 | P a g e

PROJECT RUNE-X

now  have  sizeable  public  datasets  and  established  ML  baselines  demonstrating

classification and recognition potential under constrained conditions (Wang P. , et al.,

2024)  (Zheng,  Chen,  Wang,  Qi,  &  Yan,  2024).  Similarly,  synthetic-data  generation

methods  have  enabled  robust  model  training  for  Old  Aramaic  inscriptions  despite

limited  real-world  samples, proving  that  deep-learning  systems  can  generalise  from

artificially generated variations (Aioanei A. C., Hunziker-Rodewald, Klein, & Michels,

2023). These research directions justify a scalable architectural design that supports

transfer  learning,  domain  adaptation,  and  augmentation  pipelines  for  new  scripts

across different regions and periods.

Rune-X also aims to integrate seamlessly with institutional workflows. Museums often

need  tools  for  annotating  inscriptions  on  artefacts;  archaeology  labs  need  support

identifying  fragments  or  reconstructing  damaged  texts;  libraries  require  indexing  of

ancient  manuscripts;  national  archives  need  solutions  aligned  with  long-term

preservation mandates. Rune-X is designed to function as both an internal research

tool  and  a  SaaS  platform,  allowing  institutions  to  upload  digitised  images,  manage

collections, export structured results, and feed findings back into their catalogues. The

system’s extensibility ensures compatibility with emerging imaging techniques such as

3D  scanning,  X-ray  tomography,  and  multispectral  imaging  —  methods  that  have

already proven successful in revealing hidden or unreadable text in cases such as the

Herculaneum scrolls.

Critically, Rune-X is built with long-term sustainability in mind. As datasets grow and

model  performance  improves  through  self-supervised  learning,  the  platform  is

expected to increase in accuracy and semantic robustness, allowing for progressively

deeper linguistic and archaeological insights. This cumulative improvement reflects a

core principle: Rune-X is not merely a tool, but an evolving AI research infrastructure

for  computational  archaeology  and  historical  linguistics.  By  continuously  integrating

new  corpora,  imaging  datasets,  and  reconstructed  outputs,  Rune-X  becomes  more

capable over time and more valuable to institutions worldwide.

Ultimately,  the  long-term  vision  of  Rune-X  is  to  transform  cultural-heritage  archives

from isolated collections of images into a living knowledge system. Rather than serving

merely  as  digital  replicas,  ancient  texts  and  inscriptions  become  interconnected,

interpretable, and computationally searchable. By bridging AI, archaeology, linguistics,

and philology, Rune-X seeks to define a new technological category — heritage AI —

13 | P a g e

PROJECT RUNE-X

that  enables  unprecedented  access  to  humanity’s  linguistic  past  and  empowers

researchers, educators, and institutions worldwide.

14 | P a g e

PROJECT RUNE-X

5. Technical Architecture Overview

Rune-X  is  designed  as  a  modular,  multimodal  artificial-intelligence  system  that

transforms raw images of ancient inscriptions into structured, interpretable linguistic

outputs. Its architecture is intentionally layered: each core module addresses a specific

weakness found in traditional OCR, existing epigraphic workflows, or current machine-

learning  approaches  to  ancient  scripts.  The  high-level  pipeline  consists  of  three

primary subsystems: the Glyph Tokenisation Engine, the Semantic Transformer Model,

and  the  Generative  Reconstruction  Module,  integrated  within  a  surrounding  data

ingestion, preprocessing, and output framework.

At  the  entry  point,  digitised  inputs  originate  from  photographs,  2D  scans,  or  more

advanced imaging modalities such as high-resolution CT or multispectral imaging —

techniques increasingly used in heritage science to reveal hidden or degraded text.

Recent  successes  in  reading  the  Herculaneum  papyri,  for  example,  relied  on

combining  X-ray  phase-contrast

tomography  with  neural

inference  methods,

demonstrating the value of multi-imaging inputs for ancient-text recovery (Marchant,

How  AI  is  unlocking  ancient  texts  —  and  could  rewrite  history,  2024).  Rune-X  is

therefore designed to accommodate such sources, ensuring flexibility for institutions

that adopt advanced scanning technologies.

Once ingested, images are passed to the Glyph Tokenisation Engine (GTE). Unlike

modern  OCR,  which  assumes  clean,  contiguous,  modern  text  structures,  ancient

inscriptions typically contain irregular glyph boundaries, diverse calligraphic or carved

styles, and damage-induced fragmentation. The GTE uses a combination of contour

extraction,  stroke-pattern  analysis,  and  visual  embedding  generation  to  isolate  and

represent  individual  glyphs.  This  directly  responds  to  challenges  identified  across

ancient-script  recognition  research,  where  degradation,  variation,  and  materially

induced noise severely inhibit segmentation and feature extraction in standard models

(Diao,  et  al.,  2025).  The  output  of  this  stage  is  a  token  sequence:  a  structured

representation of glyphs as discrete units ready for semantic modelling.

The  second  subsystem,  the  Semantic  Transformer  Model  (STM),  forms  the  core

interpretative  layer.  Drawing  on  advances  in  multimodal  learning  and  transformer

architectures,  the  STM  integrates  visual  embeddings  from  the  GTE  with  contextual

and  historical  patterns  learned  during  pretraining.  This  design  is  influenced  by

15 | P a g e

PROJECT RUNE-X

demonstrated  successes  in  ancient-script  processing,  such  as  multimodal  neural

networks  that  restore  missing  ideographs  by  combining  visual  and  contextual  cues

(Duan,  Wang,  &  Su,  2024).  Rune-X  extends  this  approach  by  aligning  glyph

embeddings  with  semantic,  phonetic,  or  structural  predictions  depending  on  the

language  family.  The  STM  generates  probabilistic  interpretations,  allowing  multiple

hypotheses  for  uncertain  or  ambiguous  glyphs,  an  essential  feature  for  damaged

inscriptions.

The  third  subsystem,  the  Generative  Reconstruction  Module  (GRM),  addresses

situations  where  glyphs  are  incomplete  or  eroded.  Ancient  inscriptions  frequently

suffer material damage, leading to partial visibility or loss of key strokes. Traditional

OCR  simply  fails  under  such  conditions.  In  contrast,  generative  models  trained  on

large sets of complete characters, including synthetic variants, have shown success

in reconstructing likely glyph shapes in Old Aramaic and other scripts (Aioanei A. C.,

Hunziker-Rodewald,  Klein,  &  Michels,  2023).  Rune-X  incorporates  this  capability  to

“fill in” damaged characters, producing reconstructed versions and confidence scores.

These reconstructions feed back into the STM, improving semantic inference through

cross-module reinforcement.

Surrounding  the  core  modules,  Rune-X  includes  an  institutional  integration  layer

designed for research and archival environments. This includes metadata extraction,

provenance  tracking,  versioning  of  reconstructed  outputs,  and  export  formats

compatible  with  digital-humanities  workflows.  Outputs  may  include  transcriptions,

reconstructed  glyph

images,  semantic  metadata,  cross-reference

links,  and

uncertainty estimates. The system is built to scale, allowing incremental integration of

new scripts, corpora, and imaging sources through modular dataset loaders and fine-

tuning pipelines.

Overall,  Rune-X’s  high-level  architecture  embodies  a  shift  from  surface-level  OCR

toward  AI-assisted  philology.  By  combining  tokenisation,  semantic  inference,  and

generative  reconstruction,  the  system  is  structured  not  merely  to  read  text,  but  to

understand  it,  making  it  suitable  for  academic  research,  museum  cataloguing,

archaeological analysis, and long-term cultural preservation.

16 | P a g e

PROJECT RUNE-X

6. Deep Technical Architecture

Rune-X  is  designed  as  a  modular,  extensible,  and  multimodal  artificial-intelligence

system  that  integrates  computer  vision,  representation  learning,  transformer-based

semantics, and  generative  inference  in order to  decode  ancient  scripts  at  scale.  Its

architecture  reflects  both  the  structural  diversity  and  material  fragility  of  ancient

inscriptions.  The  system  therefore  brings  together  methods  from  ancient-script

recognition, multimodal machine learning, and image-based generative reconstruction,

drawing  on  established  findings  from  computational  epigraphy  and  from  recent

breakthroughs in the recovery of damaged historical texts. The following subsections

outline the design of each core component, the methodological rationale behind them,

and the constraints imposed by the empirical characteristics of ancient script corpora.

6.1 Glyph Tokenisation Engine (GTE)

The Glyph Tokenisation Engine (GTE) is responsible for decomposing an inscription

into discrete character-level units suitable for downstream semantic modelling. Ancient

scripts  present  difficult  segmentation  challenges:  glyph  boundaries  are  often

ambiguous,  spacing  is  inconsistent,  and  stroke  morphology  varies  substantially

depending on era, carving or writing tool, and material substrate. Damage from erosion,

cracking, or surface loss further complicates segmentation. These issues have been

widely described in surveys of ancient-script recognition, which note that conventional

OCR segmentation pipelines are inadequate for archaeological image conditions.

To  address

these  difficulties,  Rune-X  begins  with  a  preprocessing  pipeline

incorporating illumination correction, denoising, and contour enhancement. Because

inscriptions are frequently photographed or scanned under uneven lighting or across

weathered  and  multi-material  surfaces,  the  system  employs  adaptive  histogram

equalisation  and  edge-preserving  filters  to  highlight  stroke  evidence  without

introducing  artificial  structure.  Following  preprocessing,  the  GTE  applies  a  hybrid

stroke-extraction  strategy  that  combines  classical  contour-detection  algorithms  with

deep-learning-based region proposal. Contour detection helps approximate the shape

and extent of incomplete characters, while region-proposal networks (similar to those

used  in  object  detection)  identify  glyph  candidates  even  when  strokes  are

17 | P a g e

PROJECT RUNE-X

discontinuous  or  partially  missing.  This  approach  reflects  practical  insights  from

oracle-bone  and  bronze-inscription  recognition  research,  where  geometric  methods

alone cannot reliably isolate degraded glyphs.

Once  candidate  regions  are  identified,  each  region  is  transformed  into  a  visual

embedding  by  means  of  either  a  convolutional  encoder  or  a  lightweight  vision

transformer  (ViT),  depending  on  the  complexity  of  the  script  and  computational

constraints. These visual embeddings constitute the “glyph tokens” that form the input

sequence for semantic modelling. The GTE therefore outputs a structured sequence

of  glyph  embeddings,  each  accompanied  by  bounding-box  metadata,  a  confidence

score, and surface-form descriptors such as stroke count and contour complexity.

6.2 Semantic Transformer Model (STM)

The Semantic Transformer Model (STM) serves as the interpretative core of Rune-X.

Its  purpose  is  to  map  the  visual  embeddings  produced  by  the  GTE  onto  semantic

predictions,  which  may  include  phonetic  readings,  glosses,  structural  labels,  or

contextual functions depending on the writing system involved. The STM is built as a

multimodal transformer that integrates visual embeddings with contextual embeddings

derived  from  ancient  corpora  and,  where  available,  historical-linguistic  priors.  This

architectural strategy is motivated by evidence from multimodal ideograph-restoration

research,  which  has  shown  that  combining  visual  features  with  contextual  cues

substantially  improves  the  restoration  of  damaged  characters  (Duan,  Wang,  &  Su,

2024).

The  pretraining  of  the  STM  relies  on  self-supervised  learning  methods  designed  to

cope  with  the  scarcity  of  labelled  ancient-script  datasets.  Masked  glyph  prediction

allows  the  model  to  infer  missing  portions  of  characters;  contrastive  learning

encourages  alignment  between  visual  and  semantic  embeddings;  and  stroke-level

augmentation, such as synthetic erosion or edge dropout, enables the model to learn

representations  robust  to  degradation.  The  need  for  such  approaches  is  well

documented  in  computational  epigraphy,  where  researchers  have  emphasised  the

limited availability of annotated corpora and the importance of synthetic augmentation

for model stability (Aioanei A. C., Hunziker-Rodewald, Klein, & Michels, 2023).

18 | P a g e

PROJECT RUNE-X

During  inference,  the  STM  generates  a  probability  distribution  over  possible

interpretations for each glyph. For phonetic scripts, this may include ranked candidate

readings;  for  logographic  or  ideographic  systems,  it  may  include  glosses,  classifier

categories, or functional labels. Because ancient inscriptions are often fragmentary,

the  STM  incorporates  sequence-level  contextual  coherence,  allowing  ambiguous

glyphs  to  be  interpreted  in  light  of  surrounding  elements.  This  sequence-level

reasoning  is  essential  for  making  sense  of  damaged  or  stylistically  inconsistent

inscriptions.

6.3 Generative Reconstruction Module (GRM)

Given that ancient inscriptions are often incomplete, eroded, or physically damaged,

Rune-X  includes  a  Generative  Reconstruction  Module  (GRM) capable  of  producing

plausible restorations of missing or degraded glyph regions. The GRM may employ

several forms of generative modelling, including variational autoencoders trained on

complete  glyphs,  diffusion  models  conditioned  on  partial  stroke  evidence,  or

adversarial architectures designed to preserve stylistic and historical characteristics of

the script.

Training  the  GRM  requires  exposing  it  to  realistic  patterns  of  glyph  damage.  To

accomplish  this,  Rune-X  introduces  controlled  degradation  into  the  training  set  by

deleting strokes, simulating erosion, breaking edges, or injecting structural noise into

known  glyphs.  This  strategy  enables  the  model  to  learn  both  the  manifestation  of

damage and the corresponding reconstruction patterns. The approach is consistent

with synthetic-data methodologies used in Old Aramaic inscription modelling, where

artificially  aged  or  eroded  samples  were  shown  to  improve  reconstruction  and

classification  performance  under  low-resource  conditions  (Aioanei A.  C.,  Hunziker-

Rodewald, Klein, & Michels, 2023).

At  inference  time,  the  GRM  produces  a  reconstructed  glyph  image,  a  pixel-level

confidence  heatmap,  and  a  latent  embedding  that  is  subsequently  used  to  refine

predictions  in  the  STM.  This  integration  ensures  that  reconstructed  forms  are  not

treated  as  independent  artefacts  but  are  embedded  within  a  broader  semantic  and

visual reasoning process.

19 | P a g e

PROJECT RUNE-X

6.4 Dataset Pipeline

The dataset pipeline provides the infrastructure through which Rune-X ingests corpora

across  scripts,  regions,  and  imaging  modalities.  Because  heritage  institutions  now

digitise  inscriptions  through  diverse  means,  including  conventional photography, 2D

scanning,  X-ray  tomography,  and  multispectral  imaging,  the  system  is  designed  to

handle  heterogeneous  inputs.  The  inclusion  of  CT  and  X-ray  imaging  aligns  with

successful  applications  in  the  decoding  of  carbonised  Herculaneum  scrolls,  where

machine-learning methods were used in conjunction with volumetric scans to reveal

otherwise inaccessible text (National Endowment for the Humanities (NEH), 2024).

Where labelled datasets exist, Rune-X uses them for supervised fine-tuning; however,

in  many  ancient-script  domains,  labelled  data  remain  scarce,  making  synthetic

augmentation  and  weak  supervision  essential  components  of

the  pipeline.

Augmentation strategies include generating script-evolution variants, which is viable

in  the  context  of  Chinese  script  evolution  datasets  such  as  EVolution  Oracle  Bone

Characters (EVOBC) (Wang P. , et al., 2024), as well as damage synthesis and style

transfer  across  historical  periods.  These  strategies  ensure  broad  coverage  of  both

temporal variation and material degradation.

6.5 System Infrastructure

Rune-X is deployed as a scalable inference architecture capable of supporting both

research environments and institutional SaaS deployment. The system is optimised

for  GPU-accelerated  inference  (ideally  on  NVIDIA  A-series  hardware)  and  may

optionally  employ  distributed  training  to  support  large  corpora  or  multi-script

pretraining.  Its  cloud  architecture  is  organised  through  modular  microservices

corresponding  to  the  main  subsystems:  a  GTE  service  for  segmentation  and

embedding  extraction,  an  STM  inference  service  for  semantic  modelling,  a  GRM

service

for  generative  reconstruction,  and  additional  services

for  metadata

management, indexing, and request brokering via an API gateway.

Outputs generated by these services are stored within a version-controlled repository.

This  versioning  ensures  that  original,  reconstructed,  and  semantically  enriched

20 | P a g e

PROJECT RUNE-X

outputs  can  be  compared  over  time,  facilitating  transparency  in  reconstruction  and

interpretative  reasoning  —  an  important  requirement  for  academic  and  cultural-

heritage workflows.

6.6 Benchmarking and Evaluation (Planned)

The  evaluation  protocol  for  Rune-X  will  incorporate  multiple  dimensions,  including

recognition accuracy, reconstruction fidelity (measured through similarity or perceptual

metrics), semantic coherence scores, robustness under simulated degradation, and

cross-script generalisation. Publicly available datasets will serve as benchmarks, with

oracle  bone  corpora  and  the  EVOBC  dataset  constituting  initial  baselines.  As

additional  corpora  and  imaging  modalities  are  integrated,  the  evaluation  framework

will expand accordingly to ensure that the system’s performance remains stable and

interpretable across scripts and conditions.

21 | P a g e

PROJECT RUNE-X

7. Product Architecture & UX Flow

Rune-X  is designed  not  only as  a  research-oriented AI engine but  also as  a  robust

software  product  capable  of  supporting  institutional  workflows  across  museums,

archives,  archaeological  laboratories,  and  digital-humanities  centres.  Its  product

architecture  emphasises  usability,  interoperability,  and  scalability,  ensuring  that

complex AI-driven  analysis  can  be  accessed  through  intuitive  interfaces  and  well-

structured  APIs.  The  system  combines  a  modern  service-oriented  backend

architecture  with  a  streamlined  user  experience,  allowing  both  technical  and  non-

technical stakeholders to interact with its capabilities.

At a high level, Rune-X operates through an interaction loop in which users upload

digitised inscriptions or manuscripts, initiate automated analysis, review intermediate

and  final  outputs,  and  optionally  export  results  to  external  research  management

systems.  This  loop  is  supported  by  an  orchestration  layer  that  coordinates

communication  between  the  Glyph  Tokenisation  Engine,  the  Semantic  Transformer

Model,  and

the  Generative  Reconstruction  Module.  From  a  product-design

perspective, Rune-X seeks to abstract away the underlying computational complexity,

presenting  users  with  a  logically  sequenced  workflow  that  matches  established

practices in cultural-heritage digitisation.

The  user  journey  typically  begins  with  a  dedicated  upload  interface  through  which

researchers or institutional staff submit images or imaging-derived data. The platform

supports conventional image formats as well as advanced modalities such as X-ray

tomography or multispectral layers, reflecting their increasing use in cultural-heritage

reconstruction  (National  Endowment  for  the  Humanities  (NEH),  2024).  During

ingestion, the system performs validation checks to ensure that the files are readable,

appropriately  formatted,  and  associated  with  relevant  contextual  metadata  such  as

provenance, excavation identifiers, catalogue numbers, or imaging parameters. This

metadata is preserved throughout the pipeline to ensure traceability and reproducibility

— two essential standards in digital humanities and computational archaeology.

Once the user confirms the upload, the system transitions into the analysis phase. The

interface displays real-time or near-real-time progress updates as the GTE segments

the inscription into glyph candidates, the STM evaluates semantic predictions, and the

GRM  reconstructs  eroded or incomplete  forms. Although the  back-end  computation

22 | P a g e

PROJECT RUNE-X

relies on distributed processing and GPU acceleration, the interface presents these

operations in an accessible manner, allowing users to observe how individual glyphs

evolve  from  raw  image  segments  into  reconstructed,  interpreted  units.  This

transparency is critical for fostering trust in the system’s reconstructions and semantic

predictions, particularly in academic contexts where interpretative authority must be

clearly justified.

After  analysis  is  complete,  users  access  a  review  interface  that  displays  the

reconstructed  glyph  sequence,  visual  heatmaps  indicating  the  GRM’s  confidence,

semantic  labels  or  readings  generated  by  the  STM,  and  intermediate  visual

embeddings. Each glyph can be inspected individually, with both the original image

region  and  the  reconstructed  version  displayed  side  by  side.  This  design  reflects

methodologies  in  palaeography  and  epigraphy,  where  scholars  frequently  compare

original  inscriptions  with  proposed  reconstructions.  The  platform  further  supports

annotation and commentary, enabling researchers to attach notes, propose alternative

interpretations,  or  highlight  areas  requiring  manual  verification.  These  annotations

become part of  the  project’s  permanent  record  within  Rune-X  and  can  be  exported

with outputs.

In  addition  to  the  graphical  interface,  Rune-X  provides  a  comprehensive  set  of

RESTful API endpoints that allow advanced users (such as partner institutions, digital-

archive  platforms,  or  computational  humanities  researchers)  to  incorporate  Rune-X

into larger analytical workflows. APIs support batch ingestion of images, asynchronous

retrieval  of  results,  programmatic  access  to  reconstruction  and  semantic  metadata,

and integration with external databases. This interoperability ensures that Rune-X can

function  as  both  a  standalone  research  tool  and  an  embedded  component  within

broader heritage digitisation infrastructures.

Export functionality is an essential aspect of the product architecture. Rune-X allows

users  to  export  reconstructed  glyphs,  machine-readable  transcriptions,  semantic

metadata, and model-confidence metrics in formats commonly used by museums and

research  libraries,  such  as  JSON-LD  for  linked  open  data,  TEI-XML  for  scholarly

textual encoding, or high-resolution image formats for digital catalogues. These export

capabilities  ensure  compatibility  with  existing  digital  collections  and  facilitate  cross-

institutional research.

23 | P a g e

PROJECT RUNE-X

From a UX perspective, the system emphasises clarity, context, and auditability. Each

stage of processing is surfaced to users, not merely as a technical necessity, but as

part  of  a  design  philosophy  that  respects  the  academic  importance  of  interpretive

transparency.  Researchers  can  trace  every  output  back  to  its  computational  origin,

including the preprocessing parameters, tokenisation decisions, semantic scores, and

reconstruction  embeddings.  This

level  of  explainability

reflects  established

expectations in both machine learning and heritage studies, where provenance and

process documentation are central to scholarly credibility.

In sum, the product architecture of Rune-X integrates a sophisticated AI back-end with

a  user  experience  tailored  to  the  workflows  of  cultural-heritage  and  academic

institutions.  By  providing  intuitive  interfaces,  comprehensive  APIs,  rich  annotation

capabilities, and export formats aligned with international standards, Rune-X functions

as  a  practical  tool  for  large-scale  heritage  interpretation  rather  than  a  theoretical

demonstration.  Its  design  anticipates  both  contemporary  research  needs  and  the

emerging  technological  ecosystem  of  digital  humanities,  positioning  it  as  a

foundational platform for heritage AI.

24 | P a g e

PROJECT RUNE-X

8. Market & Customer Analysis

The  market  for  automated  ancient-script  analysis  emerges  at  the  intersection  of

cultural-heritage  preservation,  academic  research  infrastructure,  and  the  rapidly

expanding  global  digitisation  economy.  Worldwide,  institutions  are  digitising  cultural

assets at unprecedented speed, driven both by preservation imperatives and by the

shift toward open-access digital archives. According to a UNESCO global assessment,

over  100,000  libraries  and  archives  across  at  least  160  countries  are  engaged  in

digitisation  programmes,  collectively  producing  tens  of  millions  of  images  annually

(UNESCO, 2024).

Yet,  UNESCO  also  reports  that  digitised  materials  frequently  lack  semantic

interpretation,  stating  that  “digital  replicas  often  remain  silent  images,  without

metadata, transcription, or contextualisation.” This structural gap creates substantial

demand for interpretative technologies such as Rune-X, which transform image-based

archives into computationally searchable knowledge.

The primary customer segments for Rune-X are museums, national archives, research

libraries, and university departments specialising in archaeology, linguistics, history, or

digital humanities. The scale of these sectors is significant. The International Council

of  Museums  (ICOM)  estimates  that  there  are  approximately  55,000  museums

worldwide,  many  of  which  maintain  large  epigraphic,  manuscript,  or  archaeological

collections requiring digital preservation and analysis. Simultaneously, archaeological

research output has increased substantially, with major excavation projects in China,

the Middle East, Europe, and Mesoamerica producing  high volumes of inscriptions,

tablets,  manuscripts,  and  carved  artefacts.  These  institutions  collectively  face  the

same problem: digitised material accumulates faster than expert analysts can process

it.

The commercial demand for tools that augment human expertise is evident from the

rapid expansion of the cultural-heritage digitisation sector. Publicly available market

data indicate that the global Cultural Heritage Digitization Studios market was valued

at USD 2.18 billion in 2024 and is projected to grow to approximately USD 6.51 billion

by  2033,  reflecting  a  13.7%  compound  annual  growth  rate  (CAGR)  (Dataintelo).

Growth  is  driven  by  increasing  investment  in  high-resolution  imaging,  archive

management,  and  digital-access  systems  across  museums,  libraries,  and  heritage

25 | P a g e

PROJECT RUNE-X

agencies  worldwide.  Within  this  ecosystem,  AI-driven  interpretation  remains  an

underdeveloped  but  increasingly recognised requirement,  particularly as  institutions

accumulate digital surrogates at a pace that far exceeds manual transcription capacity.

The feasibility and value of AI-assisted analysis have been underscored by high-profile

breakthroughs such as the decipherment of text from carbonised Herculaneum scrolls

using machine learning and CT-based imaging. These demonstrations serve both as

proof-of-concept  achievements  and  as  strong  demand  signals,  indicating  that

institutions increasingly view AI-assisted interpretation tools like Rune-X as essential

components of the next generation of cultural-heritage infrastructure.

Universities  and  research  centres  represent  another  major  customer  class.

Departments  of  archaeology,  ancient  history,  epigraphy,  philology,  computational

linguistics, and digital humanities all rely on inscriptions and historical manuscripts for

primary research. Yet these departments face chronic shortages of trained specialists

capable of large-scale manual transcription, a challenge well documented in ancient-

script research communities. As a result, academic institutions increasingly seek tools

that support annotation, reconstruction, and computational analysis. Rune-X, with its

multimodal semantic inference and reconstruction capabilities, provides a systematic

framework for accelerating research and reducing manual workload. Its ability to ingest

large  corpora  and  produce  structured  outputs  makes  it  compatible  with  digital-

humanities methodologies such as TEI-XML encoding, linked open data, and large-

scale comparative linguistic analysis.

Government  heritage  agencies  and  national  libraries  also  represent  an  important

segment. Many countries are now implementing long-term digital-heritage strategies

aligned  with  UNESCO  memory-preservation  initiatives.  These  organisations  must

manage extensive archives spanning multiple languages and eras, including ancient

Chinese  inscriptions,  cuneiform  tablets  from  Iraq,  hieroglyphic  records  from  Egypt,

medieval manuscripts from Europe, and heritage artefacts from Southeast Asia. The

need to interpret and make these holdings accessible is both a statutory requirement

and a cultural priority. Rune-X’s ability to serve as a unified interpretative engine across

multiple scripts and imaging modalities is aligned with these national-scale objectives.

A  final  emerging  market  lies  in  commercial  and  creative  industries,  including  game

development,  film  production,  cultural-tourism  platforms,  and  design  studios  that

require accurate reproduction of ancient scripts or reconstructed glyph forms. Although

26 | P a g e

PROJECT RUNE-X

secondary compared to museums and research institutions, this segment illustrates

the  broader  cultural  relevance  of  ancient-script  interpretation  and  the  potential  for

ancillary licensing or API-based revenue streams.

Across  all  segments,  a  common  pattern  is  evident:  institutions  have  accumulated

significant  volumes  of  digitised  heritage  content  but  lack  scalable  interpretative

capacity. Rune-X addresses this deficit by providing a production-ready, AI-assisted

interpretation platform tailored to the linguistic, material, and contextual complexities

of  ancient  scripts.  Its  positioning  at  the  convergence  of  digitisation,  AI-driven

reconstruction, and computational humanities gives it strategic relevance in a global

market increasingly prioritising cultural preservation, digital accessibility, and scholarly

transparency.

27 | P a g e

PROJECT RUNE-X

9. Competitive Landscape

As  the  field  of  computational  heritage  evolves,  several  existing  tools,  research

prototypes, and scholarly-oriented platforms aim to tackle parts of the ancient-script

interpretation problem. However, none currently deliver a comprehensive, production-

ready system that combines glyph-level tokenisation, semantic inference, generative

reconstruction,  cross-script  flexibility,  and  institutional-grade  export  &  integration. A

survey of the leading approaches illustrates both the progress made and the remaining

gaps — gaps that Rune-X is designed to fill.

9.1 Existing OCR & Historical Document Platforms

Several platforms and systems target historical or handwritten document recognition.

For example, Transkribus is widely used for transcribing European manuscripts and

early-modern documents; it supports line segmentation, handwritten-text recognition,

and  export  in  TEI/XML  format.  (Wikipedia,  n.d.). Another  is  eScriptorium,  an  open-

source  transcription  tool for historical manuscripts  and  printed  books,  built  on  OCR

engines  like  Kraken  and  designed  for  manual  or  semi-automated  transcription

workflows  (Wikipedia,  n.d.).  These  platforms  are  mature  and  production-ready  for

certain classes of historical text, such as medieval manuscripts, early printed books,

18–19th  century  documents.  However,  they  are  designed  primarily  for  modern  or

early-modern scripts and languages; they lack the structural and semantic machinery

required  for  ancient  inscriptions  or  glyph-based  scripts  like  oracle  bone,  cuneiform,

hieroglyphs. As such, they are not suited to the task that Rune-X aims to address.

9.2 Script-Specific Machine Learning Research & Prototypes

In recent years, a wave of academic research has targeted recognition of ancient or

non-standard  scripts.  For  example,  a  comprehensive  survey  titled  Ancient  Script

Image  Recognition  and  Processing: A  Review  documents  the  challenges  common

across ancient scripts, including data imbalance, degradation, and symbol variety, and

analyses existing recognition approaches from 2000 to 2024, showing a rising number

of deep-learning studies tackling such problems (Diao, et al., 2025).

28 | P a g e

PROJECT RUNE-X

Script-specific studies have demonstrated  viability  in  constrained  contexts. A  recent

paper Deep Aramaic: Towards a Synthetic Data Paradigm Enabling Machine Learning

in  Epigraphy  simulates  large-scale  datasets  of  Old  Aramaic  inscriptions  using

synthetic data generation combined with neural networks; despite the scarcity of real-

world  annotated  data,  the  authors  achieve  meaningful  classification  performance

(Aioanei A. C., Hunziker-Rodewald, Klein, & Michels, 2023). Other work demonstrates

deep-learning-based recognition on ancient Tamil inscriptions, using a region-based

convolutional neural network (RCNN) approach able to tolerate stylistic variation and

surface degradation (Umamageswari, Deepa, Sherin Beevi, & Sangari, 2025).

Furthermore,  some  recent  research  points  toward  generative  reconstruction  and

restoration of damaged glyphs — for instance, using diffusion or GAN-based models

to fill in missing strokes, or applying OCR to stone inscriptions and historical artifacts

(Julian & R, 2023).

These  research  efforts  show  that  pieces  of  the  ancient-script  decoding  puzzle  are

solvable:  recognition,  classification,  augmentation,  restoration.  But  each  tends  to

address only a single dimension (for example, classification or restoration) and often

within a single script family.

9.3 Key Limitations and Gaps in Existing Solutions

Despite meaningful progress in ancient-script recognition, current tools and research

prototypes exhibit several structural limitations that prevent them from functioning as

comprehensive solutions for museums, archives, and large-scale digitisation initiatives.

The first limitation concerns scope. Existing machine-learning approaches frequently

focus on a single writing system, for example, Old Aramaic or ancient Tamil inscriptions,

and  are  rarely evaluated across  multiple  scripts,  mediums, or chronological  stages.

This script-specific orientation limits cross-domain applicability and restricts the ability

of institutions to adopt such models for diverse collections.

A  second  constraint  is  the  absence  of  semantic  interpretation  within  most  research

pipelines. Studies that achieve success in classification or basic recognition typically

stop at  identifying glyphs  or characters, without  modelling  the  semantic  or phonetic

relationships  necessary  for  interpreting  inscriptions  in  context. The  2025  survey  on

29 | P a g e

PROJECT RUNE-X

ancient-script  image  processing  notes  that  semantic  decoding  remains  largely

unaddressed  across  the  field,  as  most  systems  focus  on  either  segmentation  or

classification rather than contextual understanding (Diao, et al., 2025).

Third,  existing  research  typically  separates  reconstruction  and  interpretation  into

distinct processes.  Some  studies  demonstrate  the use  of  generative  approaches  to

restore  damaged glyphs,  while others focus  on  recognition of  intact  characters, but

integrated  reconstruction-plus-semantics  pipelines  are  rare.  This  divide  prevents

current tools from addressing the realities of archaeological data, where inscriptions

are often simultaneously fragmentary, stylistically irregular, and semantically complex.

A  fourth  limitation  concerns  workflow  integration.  Tools  such  as  Transkribus  and

eScriptorium  perform  well  in  historical-manuscript  domains  (European  handwritten

texts, early-modern prints), but they do not support the provenance tracking, metadata

export  standards,  or  batch-processing

features  required  by  cultural-heritage

institutions  working  with  inscriptions  on  stone,  bone,  metal,  papyri,  or pottery. Their

OCR-oriented  architectures  further  assume  regular  line  structure  and  relatively

undamaged surfaces, assumptions that do not hold in most archaeological collections.

Finally, the scarcity of large, labelled datasets remains a fundamental obstacle. While

synthetic-data  techniques  help  mitigate  this  issue,  studies  frequently  report  that

artificially  generated  samples  do  not  fully  capture  the  material  variability  of  real

inscriptions,  resulting  in  domain-transfer  limitations  when  models  are  applied  to

authentic  archaeological  artefacts  (Aioanei  A.  C.,  Hunziker-Rodewald,  Klein,  &

Michels,  2023).  This  challenge  reinforces  the  inability  of  current  systems  to  scale

reliably across institutions, artefact types, and imaging conditions.

Taken  together,  these limitations  demonstrate  that  although  isolated  components  of

ancient-script analysis have been explored, no existing solution delivers the unified,

end-to-end capacity required for large-scale heritage digitisation or academic research

workflows.

9.4 Rune-X’s Comparative Advantage

Rune-X  is  designed  as  a  direct  response  to  the  structural  gaps  observed  across

existing  tools,  research  prototypes,  and  institutional  workflows.  Its  architecture

30 | P a g e

PROJECT RUNE-X

integrates segmentation, reconstruction, semantic modelling, and knowledge export

into a single multimodal pipeline. By unifying these processes, Rune-X offers a level

of  completeness  that  surpasses  the  narrow  focus  of  script-specific  or  task-specific

systems. The Glyph Tokenisation Engine handles irregular, damaged, or non-standard

glyph boundaries; the Semantic Transformer Model provides contextual interpretation

across  sequences  rather  than  isolated  glyph  classification;  and  the  Generative

Reconstruction  Module  restores  missing  or  eroded  sections,  allowing  the  semantic

model  to  operate  on  fuller  and  more  coherent  representations.  This  three-layer

architecture offers a degree of interpretative robustness absent in current solutions.

Rune-X’s  cross-script  orientation  further  distinguishes  it  from  existing  approaches.

Instead of restricting itself to a single writing system, the platform is built to support

multiple scripts, eras, and imaging modalities. This flexibility aligns with the growing

trend

in  cultural-heritage  digitisation,  where

institutions

increasingly  manage

collections  spanning  multiple  historical  contexts  and  linguistic  traditions.  Whereas

current research efforts remain largely siloed, Rune-X is intentionally architected for

generality and long-term extensibility.

Another key differentiator lies in Rune-X’s institutional readiness. The system provides

features such as provenance tracking, metadata preservation, audit logs, TEI-XML or

JSON-LD  export,  and  batch-processing  support  —  elements  that  are  essential  for

museums, libraries, and archives but missing from existing algorithms and research

prototypes.  The  platform’s  integration-focused  design  ensures  compatibility  with

digital-humanities  workflows  and  catalogue  systems,  bridging  the  gap  between

machine-learning research and operational heritage management.

Finally, Rune-X derives strength from its multimodal structure. By linking tokenisation,

semantic  inference,  and  generative  reconstruction  into  a  continuous  pipeline,  the

system  produces  interpretable,  verifiable  outputs  suitable  for  scholarly  use.  This

integrated design, informed by the limitations identified in recent reviews of the field

(Diao, et al., 2025), positions Rune-X not merely as a technical advancement but as a

foundational infrastructure solution for heritage AI.

31 | P a g e

PROJECT RUNE-X

10. Business Model & Revenue Strategy

The business model for Rune-X is built around the dual reality of the cultural-heritage

sector:  institutions  increasingly  digitize  artefacts  and  inscriptions,  but  lack  scalable

tools  to  convert  these  digital  assets  into  structured,  usable  knowledge.  Rune-X’s

monetization  strategy  leverages  this  unmet  need  by  offering  a  modular,  scalable,

enterprise-grade AI service tailored for heritage institutions, research centers, libraries,

and  museums.  The  revenue  strategy  combines  subscription-based  SaaS,  usage-

based  (consumption)  pricing,  and  optional  premium  services,  enabling  both  stable

recurring revenue and flexible cost alignment with institutional usage.

10.1 Core Monetization Models

Given the evolving nature of AI-enabled SaaS, Rune-X adopts a hybrid monetization

model combining:

•  Subscription-based  access:  Institutions  (museums,  archives,  universities)

can  pay  recurring  fees  for  platform  access,  benefiting  from  predictable

budgeting and broad functionality.

•  Consumption  /  usage-based  billing:  For  institutions  with  intermittent

workload (for example, occasional large inscription digitisation projects), Rune-

X  charges  based  on  actual  compute  usage  (such  as  number  of  inscriptions

processed, GPU hours consumed, or volume of data processed). This aligns

cost  with  value  delivered,  a  model  increasingly  recognised  in  AI-SaaS

businesses. Industry analysts emphasise that “consumption-based models are

a natural fit” for AI+SaaS offerings, offering fairness and scalability compared

to seat-based or flat-fee licensing (Khanna, Mittal, Wu, & Castillo, 2025).

•  Premium  /  Add-on  Services:  These  can  include  services  such  as  high-

resolution  reconstruction,  semantic  metadata  enrichment,  consultancy  for

difficult inscriptions, batch-processing priority, custom script support, or archival

integration  services.  This  allows  Rune-X  to  capture  value  beyond  baseline

automated processing, especially for large institutions or conservation projects.

32 | P a g e

PROJECT RUNE-X

This hybrid approach balances predictable revenue (via subscription) with alignment

of cost to usage. It also offers flexibility to customers of varying sizes and needs, from

small university research groups to large national heritage institutions.

10.2 Alignment  with  Heritage  Sector  Economics  &  Institutional

Needs

The  heritage and  cultural-heritage  digitisation  sector is increasingly  adopting  cloud-

based and digital-asset management workflows. Studies and industry reports note that

cultural  institutions  benefit  from  outsourcing  digital  asset  management  (DAM),

digitisation, and metadata services rather than building in-house departments, due to

high cost of storage, maintenance, and specialist labour (Mabe, n.d.).

Rune-X  positions  itself  as  a  specialized  DAM/AI-enhanced  pipeline:  it  augments

traditional  digital  asset  management  systems  by  offering  semantic  decoding,

reconstruction, and metadata enrichment — functions not covered by standard DAM

platforms. By  doing  so,  Rune-X  provides  an incremental value  layer above  existing

digital-archive tools, making it easier for institutions to adopt without overhauling their

entire workflow.

For institutions with limited technical capacity, Rune-X offers a managed service model:

rather  than  deploying  locally,  they  can  use  Rune-X’s  cloud-based  SaaS  platform,

thereby avoiding the need for specialised hardware, in-house ML teams, or long-term

maintenance. This lowers the barrier to adoption, particularly for smaller museums or

institutions in developing regions.

10.3 Value Proposition & Customer Segments

Rune-X delivers clear value propositions to distinct customer segments:

•  Large  Museums,  National  Archives,  Libraries:  Provide  scalable,  automated

inscription  and  manuscript  interpretation,  reducing  reliance  on  scarce  expert

labour;  enable  cataloguing,  conservation,  searchable  archives,  and  public

access.

33 | P a g e

PROJECT RUNE-X

•  Academic  &  Research

Institutions:  Support

large-scale  philological,

archaeological,  linguistics,  and  digital  humanities  research;  enable  rapid

transcription,  cross-era  comparative  studies,  and  metadata-rich  corpora

construction.

•  Cultural-heritage  NGOs  and  Conservation  Projects:  Facilitate  restoration,

preservation, and documentation of endangered or deteriorating artefacts; help

create digital twins and enable virtual access or research.

•  Digital-asset  management  /  DAM  providers:  Provide  a  plug-in  or  add-on  to

existing  DAM  platforms,  enriching  metadata,  reconstruction,  and  semantic

access — useful for commercial DAM vendors or institutional archives seeking

upgraded capabilities.

•  Commercial/Creative

Industries

(optional):  Provide  asset

licensing

(reconstructed  glyph  imagery,  restored  inscriptions)  for  cultural  media,

publishing, educational content,  game  development,  or  design  — offering  an

alternative revenue stream beyond institutional licensing.

10.4 Competitive & Market Strategy

Given the limited presence of comprehensive AI-powered ancient-script tools in the

heritage market, Rune-X benefits from first-mover advantage in many segments. Few

competitors  offer

full-stack  solutions  combining  segmentation,  reconstruction,

semantics,  and  institutional-grade  export/integration. As  such,  Rune-X  can  position

itself as a specialised vertical SaaS, combining domain expertise (heritage and scripts)

with cutting-edge AI.

To  ensure  adoption,  Rune-X  will  pursue  pilot  partnerships  with  leading  museums,

archives, and academic institutions; offer flexible pricing during pilots (such as usage-

based or reduced subscription); and generate academic publications or case studies

to demonstrate efficacy. This helps build credibility, reduce adoption friction, and create

reference use cases for later users.

34 | P a g e

PROJECT RUNE-X

10.5 Risk Management & Revenue Safeguards

AI-infrastructure costs, especially GPU usage, storage, and data transfer, are a known

challenge for AI-powered SaaS. Industry analysis shows that rising cloud costs can

undermine  profitability  if  not  carefully  managed,  and  many AI-SaaS  providers  now

adopt usage-based pricing to align revenue with infrastructure expenses (Cahill, 2025).

Rune-X  mitigates  this  risk  by  combining  subscription  and  consumption  pricing,

allowing high-volume users to scale cost predictably, while ensuring charges reflect

actual  compute  usage.  For  institutions  with  irregular  volume,  usage-based  billing

avoids  forcing  them  into  high  fixed  costs.  Additionally,  premium  add-ons  and

consultancy  services  provide  higher-margin  revenue  streams  that  help  offset

infrastructure overhead.

To  further  safeguard  sustainability,  Rune-X  considers  optional  hybrid  deployment

models,  including  on-premise  or private-cloud  installations  for large  institutions  with

strict data or privacy constraints (such as national archives). This flexibility supports

clients  with  regulatory  or  institutional  compliance  needs,  reducing  one  barrier  to

adoption.

35 | P a g e

PROJECT RUNE-X

11. Implementation Roadmap

The implementation roadmap for Rune-X outlines the phased strategy for transforming

the  system  from  a  validated  technical  concept  into  a  deployable,  institution-ready

platform. The roadmap balances engineering development, data acquisition, product

refinement, institutional collaboration, and compliance considerations. It is structured

around  three  major  phases:  Foundational  Development,  Integration  &  Institutional

Pilots,  and  Scaling  &  Optimisation.  Each  phase  builds  upon  the  preceding  one,

ensuring that technical maturity, stakeholder engagement, and operational readiness

evolve in parallel.

11.1 Phase I: Foundational Development (Months 1–6)

The  first  phase  prioritises  construction  of  the  system’s  core  machine-learning

architecture  and  data  pipeline.  During  this  period,  engineering  work  centres  on

implementing the Glyph Tokenisation Engine, the Semantic Transformer Model, and

the  Generative  Reconstruction  Module  in  their  functional  prototype  forms.  Parallel

efforts  include  developing  the  dataset  ingestion  framework,  establishing  the

preprocessing and normalisation routines, and integrating version-controlled storage

and provenance tracking. This phase also involves conducting baseline evaluations

on  public  datasets  from  oracle  bones,  Tamil  inscriptions,  and  other  open  sources,

allowing

the

team

to  benchmark

tokenisation  accuracy,  semantic  modelling

performance, and reconstruction fidelity.

From a product perspective, Phase I includes the creation of the initial user interface

and API gateway. The goal is not to develop a polished interface but to establish a

functional environment through which researchers or institutional partners can upload

data,  initiate  processing,  and  view  intermediate  outputs.  This  period  also  includes

instituting  internal  quality  assurance  protocols,  designing  security  and  privacy

safeguards, and defining data-handling standards consistent with practices in digital

humanities and cultural-heritage informatics.

36 | P a g e

PROJECT RUNE-X

11.2 Phase II: Integration and Institutional Pilots (Months 7–14)

Phase II focuses on deploying Rune-X in controlled pilot environments with selected

institutions. These  pilot  partnerships  serve  a  dual  purpose:  they  validate  Rune-X  in

real heritage workflows and supply diverse, institution-generated datasets that refine

model  robustness.  During  this  phase,  engineering  work  shifts  toward  usability

improvements,  metadata  export  compatibility  (for  example,  TEI-XML  or  JSON-LD),

and integration with digital-asset management systems used by museums or research

libraries.  The  interface  is  enhanced  to  support  annotation  features,  side-by-side

comparisons  of  reconstructed  and  original  glyph  segments,  and  visualisations  of

semantic predictions.

Institutional pilots also serve to refine domain adaptation. Because ancient collections

vary widely in imaging quality, material type, and script evolution, pilot data provides

essential  insight  into  how  model  components  behave  outside  controlled  laboratory

datasets. Developer-institution feedback loops, similar to those used in major digital

humanities  tool  development,  ensure  that  each  subsystem  iteratively  improves  in

accuracy, interpretability, and processing efficiency. This phase concludes with formal

evaluation  reports  documenting  performance  across  pilot  sites  and  establishing  a

validated minimum viable product for wider deployment.

11.3 Phase III: Scaling, Optimisation, and Deployment (Months

15–30)

The third phase emphasises operational scaling. With validated pilot data and a stable

MVP,  Rune-X  transitions  from  prototype to  production  platform. This  stage  includes

optimising inference latency, increasing GPU efficiency, and implementing distributed

processing

to  support

large

throughput  workloads

from  national

libraries,

archaeological labs, or regional heritage networks. The system is expanded to support

additional scripts or writing systems, based on pilot feedback and institutional demand.

Commercial deployment activities begin during this phase. Rune-X finalises its SaaS

subscription tiers, consumption-based billing structures, and institutional service-level

agreements. Documentation, training materials, onboarding workflows, and technical

support protocols are established. The product team ensures compliance with long-

37 | P a g e

PROJECT RUNE-X

term preservation standards, open-data policies, data-sovereignty requirements, and

UNESCO  Memory  of  the  World  programme  guidelines  —  factors  that  strongly

influence institutional procurement decisions.

By  the  end  of  Phase  III,  Rune-X  is  positioned  for  broad  adoption  across  heritage

organisations seeking to convert their digitised artefacts into structured, interpretable

knowledge. With a scalable infrastructure, refined user workflows, and demonstrated

accuracy across diverse inscriptions, the platform becomes capable of serving as a

foundational tool in digital archaeology, epigraphy, and computational cultural heritage.

38 | P a g e

PROJECT RUNE-X

12. Risk Assessment & Mitigation Strategy

The  development  and  deployment  of  Rune-X  involve  technical,  operational,

institutional, and ethical risks that must be addressed to ensure the platform’s long-

term  viability  and  credibility.  A  rigorous  assessment  of  these  risks  enables  the

formulation of mitigation strategies aligned with the expectations of cultural-heritage

institutions, academic collaborators, and funding bodies. The risks fall into four major

classes:  technical  limitations,  data  and  domain  constraints,  institutional  adoption

barriers, and ethical or governance concerns.

12.1 Technical Risks

The  primary  technical  risk  arises  from  the  inherent  difficulty  of  ancient-script

processing.  Ancient  inscriptions  exhibit  extreme  variability  in  material  condition,

imaging quality, stylistic diversity, and linguistic evolution. Models trained on limited or

domain-specific  datasets  may  generalise  poorly  to  new  scripts,  media  types,  or

imaging conditions. This risk is exacerbated by the scarcity of labelled corpora and the

fragmentary nature of archaeological artefacts.

Mitigation  requires  a  multi-pronged  technical  strategy.  Rune-X  incorporates  domain

adaptation  and  synthetic  augmentation  methods  to  extend  generalisability  across

scripts  and  imaging  modalities.  Continuous  benchmarking  across  diverse  datasets,

including pilot-institution corpora, ensures that model performance is monitored and

improved iteratively. Collaboration with academic institutions provides access to rare

or  high-quality  samples  that  strengthen  training  diversity.  Additionally,  the  system

adopts modular architecture to allow rapid refinement of individual components (such

as  the  tokenisation  engine  or  generative  model)  without  destabilising  the  entire

pipeline.

12.2 Data Availability and Quality Risks

Ancient-script  datasets  vary  widely  in  annotation  quality,  imaging  resolution,  and

representativeness.  While  some  corpora,  such  as  oracle-bone  datasets,  provide

structured  annotation,  many  others  lack  consistent  metadata  or  contain  only  raw

39 | P a g e

PROJECT RUNE-X

images.  Moreover,  access  to  high-value  collections  is  sometimes  restricted  by

institutional policies or cultural-heritage regulations.

Rune-X mitigates this risk through flexibility in its ingest pipeline, enabling the platform

to  process  both  well-structured  and  minimally  annotated datasets. The  system also

supports  weak  supervision  and  semi-automated  annotation  workflows,  allowing

institutions  to  gradually  improve  dataset  quality  over  time.  Pilot  partnerships  are

essential in this regard: they create controlled environments in which data standards

can be harmonised, metadata enhanced, and imaging workflows jointly optimised.

Where  access  restrictions  exist,  Rune-X  offers  on-premise  or  private-cloud

deployment modes, ensuring compliance with local governance or data-sovereignty

requirements.

12.3 Institutional and Adoption Risks

Museums,  libraries,  and  archives  face  long  procurement  cycles,  conservative

technology adoption patterns, and strict operational protocols. Even when institutions

recognise  the  value  of AI-driven  interpretation,  internal  approval  processes,  budget

constraints,  and

interoperability  concerns  can  delay  adoption.  Furthermore,

institutions may hesitate to rely on automated tools without clear evidence that outputs

are verifiable, transparent, and academically defensible.

To address these risks, Rune-X prioritises transparency and explainability across its

workflow.  The  system  preserves  provenance  metadata,  offers  visualisation  of

tokenisation and reconstruction stages, and provides confidence scores for semantic

predictions,  enabling  scholars  to  trace  interpretative  decisions.  Formal  evaluation

reports  generated  during  institutional  pilots  help  build  trust  and  provide  the

documentation required for internal committee approvals. Rune-X’s standards-based

export  formats  (such  as  TEI-XML  and  JSON-LD)  ensure  compatibility  with  existing

cataloguing  and  metadata  infrastructure,  reducing  integration  friction.  Clear  pricing

models  and  phased  onboarding  reduce  budgetary  barriers  and  demonstrate  value

before full-scale deployment.

40 | P a g e

PROJECT RUNE-X

12.4 Ethical, Cultural, and Governance Risks

Ancient inscriptions often hold cultural, religious, or community-specific significance.

Automated  reconstruction  or  interpretation  may  raise  concerns  related  to  accuracy,

representation,  or  authority.  Inappropriate  deployment  of AI  in  cultural  contexts  can

undermine community trust or conflict with stewardship principles. Additionally, some

institutions  require  strict  compliance  with  ethical  guidelines  for  handling  culturally

sensitive materials.

Rune-X  mitigates  these  risks  by  adopting  a  governance  framework  grounded  in

scholarly  transparency  and  cultural  sensitivity.  Automated  outputs  do  not  replace

human expertise; instead, the system provides interpretative hypotheses that require

scholarly  review.  Annotative  features  allow  domain  experts  to  revise  or  challenge

outputs, preserving academic integrity. Governance options such as locally deployed

instances,  restricted-access  processing,  and  full  output  explainability  support

institutions  managing  sensitive  collections.  Rune-X  additionally  follows  international

guidelines for digital heritage stewardship, including UNESCO Memory of the World

principles,  which  emphasise  preservation,  provenance,  and  respect  for  community

custodianship.

12.5 Long-Term Sustainability Risks

AI  systems

face

long-term  risks  associated  with  model  drift,

technological

obsolescence,  and  rising  computational  costs.  Without  ongoing  updates,  the

performance  of  heritage-focused  models  may  degrade  as  new  imaging  modalities,

scripts, or datasets emerge.

Rune-X addresses this by implementing a long-term maintenance plan that includes

periodic  retraining  on  newly  acquired  corpora,  continual  integration  of  emerging

research findings, and scalable optimisation of compute infrastructure. The modular

architecture  ensures  components  can  be  upgraded  independently,  while  hybrid

monetisation  models  support  ongoing  operational  funding  needed  to  maintain

infrastructure  and  model  quality.  Through  sustained  collaboration  with  academic

partners,  Rune-X  remains  aligned  with  evolving  scholarly  standards  and  long-term

cultural-preservation goals.

41 | P a g e

PROJECT RUNE-X

13. Financial Outlook and Sustainability Analysis

The financial outlook for Rune-X depends on the interplay between infrastructure costs,

institutional demand, pricing structure, and the long-term maintenance requirements

of an AI-driven heritage platform. While the cultural-heritage sector differs substantially

from commercial technology markets, it presents a stable and predictable client base

with long planning cycles, recurring budgets, and clear operational needs. As a result,

Rune-X’s financial sustainability depends not on high-volume consumer adoption, but

on establishing durable institutional partnerships supported by subscription revenue,

usage-based billing, and value-added services.

13.1 Revenue Structure and Forecast Logic

Rune-X’s  hybrid  monetisation  model  provides  the  foundation  for  revenue  stability.

Subscription-based  access  offers  predictable,  recurring  income  that  aligns  with  the

annual budgeting cycles of museums, archives, and universities. Consumption-based

pricing, in contrast, captures revenue from institutions with variable demand, such as

archaeological projects or large-scale digitisation efforts that require bursts of intensive

processing.  Premium  service  offerings,  including  custom  script  support,  advanced

reconstruction,  institutional  onboarding,  and  integration  with  existing  cataloguing

systems, contribute additional high-margin revenue streams.

The forecast logic for Rune-X therefore depends on a balance of base subscription

growth and episodic usage spikes associated with major digitisation or conservation

initiatives.  Because  cultural  institutions  often  operate  under  multi-year  grant  cycles,

particularly  when  funded  by  national  heritage  agencies,  UNESCO  programmes,  or

research  councils,  the  adoption  curve  is  gradual  but  durable.  Once  integrated  into

institutional workflows, the switching cost for heritage AI systems is high, supporting

long-term retention and consistent multi-year revenue.

13.2 Cost Structure and Operational Expenditure Dynamics

Rune-X’s  cost  structure  is  shaped  primarily  by  cloud  infrastructure  requirements,

ongoing  model  retraining,  and  personnel  costs  associated  with  machine-learning

42 | P a g e

PROJECT RUNE-X

engineering, product maintenance, and institutional support. GPU-intensive inference

and  reconstruction  represent  a  significant  portion  of  operational  expenditure,

particularly when processing large volumes of high-resolution imaging or multispectral

data.  However,  the  implementation  of  usage-based  billing  allows  costs  to  scale

proportionally  with  revenue  during  high-demand  periods,  preventing  infrastructure

expenditure from outpacing income.

Personnel  and  research  costs  remain  a  core  component  of  long-term  expenditure.

Heritage-focused AI systems require continuous updates, ingestion of new corpora,

and iterative improvement of model architectures as new imaging modalities emerge.

Collaboration with academic partners can offset some of these costs through shared

datasets, joint research projects, or externally funded initiatives. The modular design

of Rune-X further reduces technical debt, ensuring that individual components, such

as the tokenisation engine or reconstruction module, can be updated without incurring

full-system redevelopment costs.

13.3 Break-Even Considerations and Growth Horizon

The break-even horizon for a specialised institutional AI platform depends largely on

the rate of institutional acquisition and the balance between subscription-based and

usage-based  revenue.  While  cultural  institutions  often  take  longer  to  adopt  new

technologies  due  to  governance  and  procurement  protocols,  once  onboarded  they

tend to maintain long-term subscriptions and incorporate tools into core workflows. As

a result, break-even is driven less by rapid user growth and more by securing a small

number  of  anchor  clients  during  the  early  years  of  deployment.  These  anchor

institutions  (national  libraries,  large  museums,  leading  archaeological  research

centres)  can  provide  both  financial  stability  and  reputational  leverage  that  supports

further adoption.

Growth beyond the initial client base is likely to follow a phased expansion pattern.

Early adoption among major institutions creates case studies that validate the efficacy

of the system, encouraging mid-sized or regional institutions to adopt the platform. In

parallel, integration with digital-asset management systems and open-source digital

humanities platforms can broaden reach and reduce friction during onboarding. As the

system matures, additional revenue opportunities emerge from specialised services

43 | P a g e

PROJECT RUNE-X

such  as  high-fidelity  reconstruction,  cross-institutional  metadata  harmonisation,  and

consultancy for large-scale digital heritage projects.

13.4 Long-Term Sustainability and Innovation Pipeline

Sustaining Rune-X over a multi-decade horizon requires ongoing technical innovation,

institutional  engagement,  and  infrastructure  optimisation. AI-driven  interpretation  of

ancient scripts is a field characterised by rapid methodological advances, especially

in  generative  modelling,  multimodal  learning,  and  domain  adaptation.  Maintaining

relevance  therefore  requires  a  structured  research  and  development  pipeline  that

incorporates advances from academic machine-learning research, digital humanities

scholarship, and heritage imaging technologies.

Long-term  sustainability  also  depends  on  institutional  alignment.  Because  many

heritage  institutions  operate  under  national  or  international  preservation  mandates,

Rune-X  must  remain  compliant  with  evolving  standards  for  data  stewardship,  open

access,  and  cultural  heritage  management.  By  offering  transparent  provenance

tracking,  explainable  outputs,  and  governance  options  such  as  on-premise

deployment,  Rune-X  positions  itself  as  a  trustworthy  partner  in  digital  preservation.

These  features  reduce  institutional  risk  and  increase  the  likelihood  of  multi-year

contract renewals.

Finally, financial resilience is strengthened by diversification of revenue sources. While

institutional licensing forms the core of the business model, partnerships with digital-

humanities consortia, research grants, consultancy, and value-added services provide

additional  income  streams  that  stabilise  revenue  across  funding  cycles.  This

diversified model enables Rune-X to remain agile, invest in technical improvements,

and  preserve  long-term  relevance  in  a  rapidly  evolving  technological  and  cultural

landscape.

44 | P a g e

PROJECT RUNE-X

14. Conclusion

Rune-X  represents  a  significant  advancement  in  the  intersection  of  artificial

intelligence,  cultural-heritage  preservation,  and  computational  humanities.  By

integrating glyph tokenisation, semantic modelling, and generative reconstruction into

a  unified  multimodal  architecture,

the  system  addresses

the

longstanding

interpretative  bottlenecks  faced  by  museums,  archives,  and  research  institutions

worldwide. Its design is grounded in the realities of ancient-script corpora (fragmentary

inscriptions, heterogeneous imaging conditions, scarce labels, and evolving linguistic

structures) while simultaneously reflecting the methodological progress documented

in recent machine-learning and epigraphic research. Through its modular architecture

and institution-focused workflows, Rune-X bridges the gap between digitisation and

understanding,  transforming  static  digital  images  into  structured,  interpretable

knowledge.

The  technical  and  product  foundations  established  in  this  plan  demonstrate  that

automated ancient-script interpretation is now not only feasible but poised for broad

institutional  application.  The  proposed  business  model  leverages  stable,  mission-

driven demand within the heritage sector, while the implementation roadmap outlines

a  clear  path  from  prototype  development  to  scalable  deployment  across  diverse

institutional  environments.  By  incorporating  transparency,  provenance  tracking,  and

scholarly  review  into  its  core  design,  Rune-X  aligns  with  the  ethical  and  cultural

responsibilities inherent in handling historical materials. The risk assessment further

ensures  that  the  system’s  development  anticipates  technical,  operational,  and

institutional challenges, reinforcing long-term sustainability.

As  cultural-heritage  institutions  continue  to  expand  their  digital  collections  and  as

global  digitisation  efforts  intensify,  the  need  for  scalable  interpretative  technologies

becomes  increasingly  urgent.  Rune-X  is  positioned  to  meet  this  need  by  offering  a

comprehensive,  academically  rigorous,  and  technologically  sophisticated  platform

capable  of  supporting  research,  preservation,  and  public  engagement.  Through

continued collaboration with museums, archives, and academic partners, Rune-X has

the  potential  to  become  a  foundational  tool  in  the  digital  transformation  of  heritage

studies,  enabling  new  discoveries,  accelerating  scholarship,  and  safeguarding

humanity’s written past for future generations.

45 | P a g e

PROJECT RUNE-X

References

Aioanei, A. C., Hunziker-Rodewald, R. R., Klein, K. M., & Michels, D. L. (19 April, 2024).

Deep Aramaic: Towards a synthetic data paradigm enabling machine learning

in

epigraphy.

PLOS

ONE,

19(4).

doi:https://doi.org/10.1371/journal.pone.0299297

Aioanei, A. C., Hunziker-Rodewald, R., Klein, K., & Michels, D. L. (11 October, 2023).

Deep Aramaic: Towards a Synthetic Data Paradigm Enabling Machine Learning

in Epigraphy. Retrieved from arXiv: https://arxiv.org/pdf/2310.07310

Anitha  Julian,  D.  R.  (2023).  Deciphering Ancient  Inscriptions  with Optical Character

Recognition.

Retrieved

from

https://eudl.eu/pdf/10.4108/eai.23-11-

2023.2343235

Cahill, C. (17 October, 2025). Software Monetization Models and Strategies  – 2026

Outlook.  Retrieved  from  Revenera:  https://www.revenera.com/blog/software-

monetization/software-monetization-models-strategies/

Dataintelo.  (n.d.).  Cultural  Heritage  Digitization  Studios  Market.  Retrieved  from

https://dataintelo.com/report/cultural-heritage-digitization-studios-market/amp

Diao, X., Bo, R., Xiao, Y., Shi, L., Zhou, Z., Xu, H., . . . Shi, D. (24 June, 2025). Ancient

Script

Image  Recognition  and  Processing:  A  Review.  Retrieved

from

ResearchGate:

https://www.researchgate.net/publication/392980270_Ancient_Script_Image_

Recognition_and_Processing_A_Review

Duan,  S.,  Wang,  J.,  &  Su,  Q.  (11  March,  2024).  Restoring  Ancient  Ideograph:  A

Multimodal  Multitask  Neural  Network  Approach.  Retrieved

from  arXiv:

https://arxiv.org/pdf/2403.06682

Henshall,  W.  (5  February,  2024).  An Ancient  Roman  Scroll  on  Pleasure  Was  Just

Decoded  Using  AI.  Retrieved  from  TIME:  https://time.com/6691588/ancient-

roman-scroll-decoded-ai/

Julian, A.,  &  R,  D.  (2023).  Deciphering  Ancient  Inscriptions  with  Optical  Character

Recognition. EAI. doi:10.4108/eai.23-11-2023.2343235

46 | P a g e

PROJECT RUNE-X

Khanna,  M.,  Mittal,  N.,  Wu,  A.,  &  Castillo,  M.  (22  September,  2025).  Upgrading

software business models to thrive in the AI era. Retrieved from McKinsey &

Company:

https://www.mckinsey.com/industries/technology-media-and-

telecommunications/our-insights/upgrading-software-business-models-to-

thrive-in-the-ai-era

Kuta,  S.  (6  February,  2025).  Using A.I.,  Researchers  Peer  Inside  a  2,000-Year-Old

Scroll  Charred  by  Mount  Vesuvius’  Eruption.  Retrieved  from  Smithsonian

magazine:

https://www.smithsonianmag.com/smart-news/using-ai-

researchers-peer-inside-a-2000-year-old-scroll-charred-by-mount-vesuvius-

eruption-180986011/

Mabe,  M.  (n.d.).  How  Digital  Asset  Management  for  Museums  Preserves  Cultural

Heritage.  Retrieved  from  Aprimo:  https://www.aprimo.com/blog/how-digital-

asset-management-for-museums-preserves-cultural-heritage

Marchant,  J.  (6  February,  2024).  AI  Unravels  Ancient  Roman  Scroll  Charred  By

Volcano.

Retrieved

from

Scientific

American:

https://www.scientificamerican.com/article/ai-unravels-ancient-roman-scrolls-

charred-by-volcano/

Marchant,  J.  (30  December,  2024).  How AI  is  unlocking  ancient  texts  —  and  could

rewrite

history.

Retrieved

from

Nature:

https://www.nature.com/articles/d41586-024-04161-z

National  Endowment  for  the  Humanities  (NEH).  (13  February,  2024).  Students

Decipher  2,000-Year-Old  Herculaneum  Scrolls.  Retrieved  from  National

Endowment  for  the  Humanities  (NEH):  ttps://www.neh.gov/news/students-

decipher-2000-year-old-herculaneum-scrolls

Thea Sommerschield, Y. A., Pavlopoulos, J., Stefanak, V., Senior, A., Dyer, C., Bodel,

J., . . . Freitas, N. d. (2023). Machine Learning for Ancient Languages: A Survey.

Computational

Linguistics,

49(3),

703–747.

doi:https://doi.org/10.1162/coli_a_00481

Umamageswari, A., Deepa, S., Sherin Beevi, L., & Sangari, A. (12 May, 2025). A deep

learning approach for recognizing ancient Tamil scripts from historical artifacts.

International  Journal  of  Advanced  Technology  and  Engineering  Exploration,

12(126). doi:http://dx.doi.org/10.19101/IJATEE.2024.111100193

47 | P a g e

PROJECT RUNE-X

UNESCO.

(2024).  DIGITIZATION,  AND  PRESERVATION  OF  ANCIENT

MANUSCRIPTS

IN

EASTERN

SUDAN.

Retrieved

from

https://articles.unesco.org/sites/default/files/medias/fichiers/2024/07/Digitizatio

n%2C%20and%20preservation%20of%20ancient%20manuscripts%20.pdf.pd

f

Wang, P., Zhang, K., Wang, X., Han, S., Liu, Y., Wan, J., . . . Liu, Y. (2 September,

2024). An open dataset for oracle bone script recognition and decipherment.

Retrieved from arXiv: https://arxiv.org/pdf/2401.15365

Wang, P., Zhang, K., Wang, X., Han, S., Liu, Y., Wan, J., . . . Liu, Y. (13 February, 2024).

An open dataset for the evolution of oracle bone characters: EVOBC . Retrieved

from arXiv: https://arxiv.org/pdf/2401.12467

Wikipedia.

(n.d.).

eScriptorium.

Retrieved

from

Wikipedia:

https://en.wikipedia.org/wiki/EScriptorium

Wikipedia.

(n.d.).

Transkribus.

Retrieved

from

Wikipedia:

https://en.wikipedia.org/wiki/Transkribus

Zheng, Y., Chen, Y., Wang, X., Qi, D., & Yan, Y. (7 February, 2024). Ancient Chinese

Character  Recognition  with  Improved  Swin-Transformer  and  Flexible  Data

Enhancement

Strategies.

Sensors,

24(7).

doi:https://doi.org/10.3390/s24072182

48 | P a g e

