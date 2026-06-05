# Fiverr Gig Gallery Kit - Norland Nguyen

This kit is built from the current project: `Vietnamese_English_RAG_Assistant`.

Primary positioning:

```text
I will build a custom RAG AI chatbot for your documents, website, or internal knowledge base
```

Core proof points from the repo:

- Vietnamese and English grounded question answering.
- PDF, DOCX, TXT, Markdown, and Notion ZIP uploads.
- Website page and sitemap ingestion.
- Qdrant dense + BM25 sparse hybrid retrieval.
- Optional Cohere reranking.
- Source citations with file, page, URL, title, path, chunk, and score metadata.
- No-answer behavior when evidence is weak.
- Feedback, metrics, retrieval trace, and evidence drawer.
- Optional Slack slash endpoint, Discord bot, and Telegram bot.
- Docker Compose stack: FastAPI, worker, bots, PostgreSQL, Qdrant, and Redis.

## Fiverr Constraints To Respect

Use these as production rules before export:

- Gallery: up to 3 images, 1 video, and 2 PDFs.
- Recommended image size: `1280 x 769 px`, 72 DPI.
- Use only visuals and screenshots you own or have permission to use.
- Keep images simple, relevant, and not overloaded with technology logos.
- Gig video should be concise. For Fiverr upload, use the 70-75 second cut.
- Keep final video under `50 MB`.
- PDF portfolio can be longer, but Fiverr previews only the first 3 pages prominently, so put the strongest proof in pages 1-3.
- Do not show API keys, private customer data, email, phone number, off-platform payment links, or copyrighted assets.

## Recommended Final Gallery

Upload in this order:

1. Video: `RAG Assistant Demo - 70s Fiverr Cut`
2. Image 1: `Custom RAG AI Chatbot`
3. Image 2: `How The RAG Pipeline Works`
4. Image 3: `What You Will Receive`
5. PDF: `RAG Knowledge Assistant Case Study`

If Fiverr uses the video thumbnail as the marketplace cover, choose a thumbnail frame with the title:

```text
Custom RAG AI Chatbot
Documents, Websites, Citations
```

## Demo Data Needed From You Later

Before recording, choose one clean, public or owned dataset. Good options:

- A public company handbook or policy PDF.
- A public product documentation site.
- A public FAQ page.
- A public-domain book only if it is clearly allowed for commercial portfolio use.
- Your own synthetic demo files, which is the safest option.

Avoid:

- CVs, student reports, private reports, client data, paid books, copied Fiverr images, screenshots with accounts/API keys, and any data you cannot publicly show.

When the data is ready, prepare 3 demo questions:

1. Vietnamese question with a clear answer in the corpus.
2. English question with a clear answer in the corpus.
3. Out-of-scope question that should trigger the no-answer behavior.

Template:

```text
Vietnamese: Theo tài liệu, [specific policy/topic] được quy định như thế nào?
English: What does the document say about [specific policy/topic]?
Out of scope: What is Norland Nguyen's personal phone number?
```

## Video A - Fiverr Cut, 70-75 Seconds

Use this for the actual Fiverr Gig video.

### Storyboard

| Time | Visual | Voice-over |
|---:|---|---|
| 0-6s | Face camera, clean background. Title overlay: `Custom RAG AI Chatbot` | Do your customers or team need accurate answers from PDFs, websites, or internal knowledge bases? |
| 6-12s | Face camera continues. Lower-third: `Norland Nguyen - AI Engineer` | Hi, I am Norland Nguyen. I build custom RAG assistants that retrieve real evidence before generating an answer. |
| 12-23s | Screen recording: app dashboard, upload panel, source dashboard. | This assistant can index PDFs, DOCX files, Markdown, Notion exports, website pages, and sitemaps. |
| 23-40s | Upload or source list, then chat question in Vietnamese. | Users can ask questions in Vietnamese or English, and the chatbot searches the indexed knowledge base instead of guessing. |
| 40-52s | Chat answer appears. Open evidence drawer with citation cards and retrieval trace. | Each answer can include source citations, page or URL metadata, evidence snippets, retrieval scores, and a trace for review. |
| 52-62s | Show no-answer state, feedback buttons, metrics strip. | The system can also say when it cannot find enough evidence, collect feedback, and track latency and usage metrics. |
| 62-72s | Architecture overlay: `Documents -> Processing -> Hybrid Retrieval -> LLM -> Answer with Citations` | You receive organized source code, Docker setup, API documentation, and a solution adapted to your data and deployment needs. |
| 72-75s | Final card: `Contact me before ordering` | Please contact me before ordering so I can review your data and recommend the right package. |

### Exact Voice-over

```text
Do your customers or team need accurate answers from PDFs, websites, or internal knowledge bases?

Hi, I am Norland Nguyen. I build custom RAG assistants that retrieve real evidence before generating an answer.

This assistant can index PDFs, DOCX files, Markdown, Notion exports, website pages, and sitemaps.

Users can ask questions in Vietnamese or English, and the chatbot searches the indexed knowledge base instead of guessing.

Each answer can include source citations, page or URL metadata, evidence snippets, retrieval scores, and a trace for review.

The system can also say when it cannot find enough evidence, collect feedback, and track latency and usage metrics.

You receive organized source code, Docker setup, API documentation, and a solution adapted to your data and deployment needs.

Please contact me before ordering so I can review your data and recommend the right package.
```

### On-screen Text

Use short overlays only:

```text
Custom RAG AI Chatbot
PDF | DOCX | Markdown | Notion ZIP
Website & Sitemap Ingestion
Vietnamese + English Q&A
Source Citations
Hybrid Retrieval
No-Answer Handling
Docker + FastAPI + Qdrant
Contact me before ordering
```

## Video B - Extended Portfolio Demo, 2-4 Minutes

Use this version for README, portfolio review, or as your master recording. Cut it down later for Fiverr.

Target length: 3 minutes 10 seconds.

### Storyboard

| Time | Visual | Notes |
|---:|---|---|
| 0:00-0:10 | Face camera. Lower-third: `Norland Nguyen - AI Engineer` | Build trust early. |
| 0:10-0:25 | Show app home screen: metrics strip, sources panel, chat panel, evidence drawer button. | Do not show browser bookmarks or accounts. |
| 0:25-0:50 | Upload a safe demo PDF/Markdown/Notion ZIP. Show `indexed with X chunks`. | Use owned/public data only. |
| 0:50-1:15 | Ingest a website page or sitemap. Show queued job and source dashboard status. | If worker takes time, use jump cut. |
| 1:15-1:50 | Ask Vietnamese question. Show answer with citation tokens. | Example depends on selected corpus. |
| 1:50-2:15 | Open evidence drawer. Show citation cards, file/page or URL/path, quote, score. Switch to trace tab. | This is the strongest technical proof. |
| 2:15-2:35 | Ask English question. Show that same corpus supports English. | Keep question simple and relevant. |
| 2:35-2:55 | Ask out-of-scope question. Show no-answer behavior. | Avoid pretending the bot knows everything. |
| 2:55-3:10 | Click feedback, show metrics updated. | Demonstrates product readiness. |
| 3:10-3:30 | Architecture diagram overlay. | Keep it clean, no code wall. |
| 3:30-3:45 | Deliverables slide and CTA. | Fiverr-safe CTA only. |

### Exact Voice-over

```text
Hi, I am Norland Nguyen, an AI Engineer focused on RAG systems, LLM applications, AI agents, and data engineering.

This is a production-shaped document AI assistant for teams that need reliable answers from scattered knowledge sources.

Instead of sending a question directly to a language model, the system first indexes your files, websites, or internal knowledge base, retrieves the most relevant evidence, and then generates an answer grounded in that evidence.

The current assistant supports PDF, DOCX, TXT, Markdown, Notion export ZIP files, website pages, and sitemaps.

On the left, users can upload files, ingest a URL, sync sources, delete outdated sources, and inspect indexed documents. At the top, the dashboard shows source count, document count, chunk count, and average chat latency.

Now I will ask a Vietnamese question from the indexed data. The assistant searches the knowledge base and returns an answer with citation markers, so users can see where the information came from.

The evidence drawer shows the citation details: source title, file page or website URL, source type, quote, retrieval score, and the retrieved context. This makes the answer easier to audit than a generic chatbot response.

The same system can answer English questions from the same corpus, which is useful for bilingual teams, customer support, documentation search, internal policies, and research assistants.

When the indexed sources do not contain enough evidence, the assistant is designed to say that it cannot find a reliable answer instead of inventing details. This no-answer behavior is important for business use cases where accuracy matters.

The application also includes feedback collection, metrics, API endpoints, Docker Compose, PostgreSQL, Qdrant, Redis worker jobs, and optional Slack, Discord, and Telegram integrations.

The retrieval layer uses hybrid search with dense vectors and BM25 sparse search, with optional reranking depending on the quality and latency requirements of your project.

For delivery, you can receive organized source code, environment configuration, Docker setup, API documentation, technical notes, and deployment guidance.

Please contact me before ordering so I can review your data type, volume, integrations, preferred AI model, and deployment environment before recommending the right package.
```

### Exact Screen Actions

1. Open the app at `http://localhost:8000`.
2. Use light or dark theme. Dark theme looks more technical; light theme can be clearer for Fiverr thumbnails.
3. Upload a safe file.
4. Wait until the UI says indexed with chunks.
5. Ingest one public URL or sitemap if available.
6. Ask one Vietnamese question from the corpus.
7. Open the evidence drawer and show citations.
8. Switch from `Cites` to `Trace`.
9. Ask one English question from the corpus.
10. Ask one out-of-scope question.
11. Click `Helpful`.
12. Show metrics update.
13. End with architecture and deliverables slide.

## Image 1 - Main Cover

Purpose: Make the buyer understand the offer in 2 seconds.

Final text to place manually:

```text
CUSTOM RAG AI CHATBOT
PDF | WEBSITE | KNOWLEDGE BASE
ANSWERS WITH SOURCE CITATIONS
```

Small footer text:

```text
FastAPI | Qdrant | Docker | Gemini/OpenAI/Groq
```

Recommended layout:

- Left: big headline.
- Right: realistic product dashboard mockup with chat answer and citation cards.
- Keep text under 25 words.
- Do not use official third-party logos.

### ChatGPT Image Prompt

```text
Create a clean professional Fiverr gig cover image, 1280 x 769 px, landscape.

Subject: a custom RAG AI chatbot for documents, websites, and knowledge bases.

Composition: left side has a large empty headline area with strong contrast; right side shows a realistic SaaS dashboard mockup for a document AI assistant. The dashboard includes a file upload panel, a chat window, and an evidence drawer with citation cards. The mockup should feel like a real B2B software product, not a generic AI illustration.

Visual style: modern technical product UI, sharp, high resolution, dark charcoal and off-white base, teal/green accent, restrained blue accents, clean grid, small code-like metadata details, professional AI engineering portfolio style.

Include subtle UI labels only if they are legible: Upload source, Ask your knowledge base, Citations, Page 12, Score 0.87.

Leave a clean text area on the left for manual typography. Do not add logos, brand marks, email, phone number, price, stars, ratings, badges, or copyrighted imagery. Do not use purple gradient or abstract AI robot imagery. Make it readable as a small marketplace thumbnail.
```

Manual text overlay after generation:

```text
CUSTOM RAG AI CHATBOT
PDF | WEBSITE | KNOWLEDGE BASE
ANSWERS WITH SOURCE CITATIONS
```

## Image 2 - Architecture

Purpose: Prove that this is full RAG engineering, not only UI.

Final title:

```text
HOW YOUR RAG CHATBOT WORKS
```

Pipeline:

```text
Files / Website / Notion
Processing
Chunking + Embeddings
Qdrant Hybrid Retrieval
Optional Reranking
LLM Generation
Answer with Citations
```

Small footer:

```text
FastAPI | PostgreSQL | Redis Worker | Docker
```

### ChatGPT Image Prompt

```text
Create a professional technical architecture image for a Fiverr gig, 1280 x 769 px, landscape.

Subject: how a custom RAG chatbot works for documents, websites, and Notion exports.

Composition: center-aligned pipeline diagram with seven connected stages. Use clean rectangular nodes, thin connector arrows, and small supporting icons. The flow should read from left to right or top to bottom: files and websites, document processing, chunking and embeddings, Qdrant hybrid retrieval, optional reranking, LLM generation, answer with source citations.

Visual style: premium B2B AI engineering diagram, crisp vector-like layout, high contrast, dark neutral background, off-white cards, teal/green accent arrows, small blue highlights. Minimal text, no clutter, no tiny unreadable code.

Add visual hints: document icons, website globe icon, database cylinder, search/rerank icon, language model node, citation card. Leave enough whitespace around all elements so Fiverr cropping does not cut text.

Do not include official company logos, API keys, personal contact information, fake badges, ratings, prices, or exaggerated claims like zero hallucination or 100 percent accurate.
```

Manual text overlay after generation:

```text
HOW YOUR RAG CHATBOT WORKS
Files / Website / Notion -> Processing -> Chunking + Embeddings -> Hybrid Retrieval -> LLM -> Answer with Citations
```

## Image 3 - Deliverables

Purpose: Make the buyer understand what they receive.

Final title:

```text
WHAT YOU WILL RECEIVE
```

Six boxes:

```text
Custom RAG Chatbot
Source Citations
FastAPI Backend
Vector Database
Docker Setup
Source Code + Documentation
```

Optional line:

```text
Optional: Website ingest | Authentication | Chat integrations | Cloud deployment
```

### ChatGPT Image Prompt

```text
Create a clean Fiverr gig gallery image, 1280 x 769 px, landscape.

Subject: deliverables for a custom RAG AI chatbot project.

Composition: a polished product-delivery board with six equal feature tiles in a 3 by 2 grid. Each tile should have a simple line icon and a short label area. The tiles represent: custom chatbot, source citations, FastAPI backend, vector database, Docker setup, source code and documentation.

Visual style: professional SaaS operations dashboard, crisp typography zones, high contrast, dark/light neutral palette, teal/green accent, subtle shadows, thin borders, clean spacing. The image should look practical and technical, not decorative.

Add a small optional-services strip at the bottom with abstract icons for authentication, chat integrations, website ingestion, and cloud deployment. Leave label areas clean enough for manual text overlays.

Do not include official logos, prices, contact information, customer data, rating stars, Fiverr badges, or unrealistic claims. Avoid crowded technology-logo collages and generic AI robot art.
```

Manual text overlay after generation:

```text
WHAT YOU WILL RECEIVE
Custom RAG Chatbot | Source Citations | FastAPI Backend
Vector Database | Docker Setup | Source Code + Documentation
Optional: Website ingest | Authentication | Chat integrations | Cloud deployment
```

## Optional Video Thumbnail Prompt

Use this only if you want a still frame instead of a screenshot.

```text
Create a professional video thumbnail for a Fiverr gig, 1280 x 769 px, landscape.

Subject: Norland Nguyen's custom RAG AI chatbot demo.

Composition: left side has room for a large title. Right side shows a polished document AI dashboard with a chat answer and citation cards. Add a small face-camera frame placeholder in the top-right corner, but do not create a real person's face. The image should feel like a screen recording thumbnail for a technical software demo.

Style: clean B2B SaaS, high contrast, dark neutral UI, teal/green accents, sharp details, readable at small size, not cluttered.

No logos, no prices, no email, no phone number, no rating stars, no badges, no copyrighted images, no fake UI claims.
```

Manual text:

```text
Custom RAG AI Chatbot
Real Demo: Documents, Websites, Citations
```

## PDF Portfolio - RAG Knowledge Assistant Case Study

Recommended length: 6 pages.

Important: because Fiverr previews the first 3 pages most strongly, pages 1-3 must already sell the project.

### Page 1 - Cover

```text
CUSTOM RAG KNOWLEDGE ASSISTANT
AI Chatbot for Documents, Websites, and Internal Knowledge Bases

Designed and Developed by Norland Nguyen
```

Visual:

- One clean dashboard screenshot.
- One small pipeline strip:

```text
Sources -> Retrieval -> Grounded Answer -> Citations
```

### Page 2 - Business Problem

```text
Teams often store knowledge across PDFs, DOCX files, Notion exports, Markdown docs, websites, policies, and internal databases.

Traditional keyword search can be slow, fragmented, and difficult for non-technical users.

A generic chatbot may answer fluently, but without grounding it can miss details, invent unsupported claims, or fail to show where the answer came from.
```

Use 3 problem cards:

```text
Scattered knowledge
Slow manual search
Answers without evidence
```

### Page 3 - Built Solution

```text
This project is a multi-source RAG assistant that indexes documents and web content, retrieves relevant evidence, and generates answers with source citations.

It supports Vietnamese and English questions, source-aware citation metadata, no-answer behavior, feedback, metrics, and optional chat integrations.
```

Feature bullets:

```text
PDF, DOCX, TXT, Markdown, Notion ZIP
Website page and sitemap ingestion
Hybrid dense + sparse retrieval
Answer citations and evidence drawer
No-answer handling
Dockerized deployment
```

### Page 4 - Architecture

```text
UI / API / Bots
        |
        v
FastAPI -> AskService -> Hybrid Retrieval -> Grounded Generation
        |                  |                  |
        v                  v                  v
PostgreSQL             Qdrant              Gemini/OpenAI/Groq
        |
        v
Redis Worker -> Parse -> Chunk -> Embed -> Index
```

Short explanation:

```text
The system separates ingestion, retrieval, generation, logging, and chat integrations so the solution can be adapted to different business requirements.
```

### Page 5 - Demo Screens

Use 4 screenshots:

- Upload and source dashboard.
- Vietnamese answer with citations.
- Evidence drawer with citation quote and retrieval score.
- No-answer or metrics screen.

Captions:

```text
Source management
Bilingual grounded answers
Citation inspection
Feedback and metrics
```

### Page 6 - Deliverables

```text
What can be delivered:

- Custom RAG chatbot workflow
- FastAPI backend
- Vector database integration
- File and website ingestion
- Source citations
- Docker setup
- Environment configuration template
- API documentation
- Technical documentation
- Deployment guidance

Optional depending on package:

- Authentication
- Admin dashboard
- Slack, Discord, or Telegram integration
- Cloud deployment
- Evaluation report
- Reranking and retrieval tuning
```

Final CTA:

```text
Please contact me before ordering so I can review your data, required integrations, preferred AI model, and deployment environment.
```

## Recording Checklist

Before recording:

- Use a clean browser profile.
- Hide bookmarks, extensions, account emails, and desktop notifications.
- Do not open `.env`, terminal history with keys, cloud consoles, or private folders.
- Use sample data that is public, owned, or synthetic.
- Index the corpus before the final take if ingestion is slow.
- Prepare three questions in advance.
- Set browser zoom to 90-100 percent.
- Use 1920 x 1080 screen recording.
- Record voice in a quiet room.
- Export MP4 under 50 MB for Fiverr.

Good screen states to capture:

- App empty state.
- Upload success with chunk count.
- Source dashboard with indexed documents.
- URL or sitemap queued/indexed.
- Vietnamese answer.
- English answer.
- Evidence drawer citations.
- Retrieval trace.
- No-answer response.
- Feedback saved.
- Metrics strip.

## Final Export Names

```text
norland-rag-chatbot-fiverr-video-75s.mp4
norland-rag-chatbot-cover-1280x769.png
norland-rag-architecture-1280x769.png
norland-rag-deliverables-1280x769.png
norland-rag-knowledge-assistant-case-study.pdf
```

## What To Update After You Choose Demo Data

Replace these placeholders:

- `[specific policy/topic]`
- `[safe demo PDF name]`
- `[safe public website URL]`
- `[actual citation page]`
- `[actual answer quote]`
- `[actual chunk count]`
- `[actual latency from metrics]`

After you provide the dataset, update:

- Exact Vietnamese demo question.
- Exact English demo question.
- Exact no-answer question.
- Exact citation examples shown in images/PDF.
- Final voice-over references if a source type is not used.
