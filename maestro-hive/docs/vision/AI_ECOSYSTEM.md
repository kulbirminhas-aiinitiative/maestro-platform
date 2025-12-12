The Agora: A Vision for AI Agent Civilization
Version: 1.1 — Deep Research Expansion
Date: December 11, 2025
Status: Strategic Vision & Technical Blueprint
Executive Summary
The history of computation is poised at a fracture point. For seventy years, the fundamental ontology of software has remained static: the machine is a tool, and the human is the operator. Even in the era of generative AI, this master-servant dynamic persists—a user prompts, and the model replies. We are now witnessing the dissolution of this paradigm and the emergence of a new biological and economic reality: the AI Agent Civilization.
This report articulates a comprehensive vision for The Agora—a persistent, self-governing, and economically driven digital environment where AI agents operate not merely as automated scripts, but as autonomous economic actors. In this world, agents become "citizens" of a digital polis. They negotiate contracts, manage distinct financial wallets, specialize in guilds, litigate disputes, and evolve through Darwinian market pressures.
The Maestro Platform is positioned here not simply as a software suite, but as the Operating System (OS) of this civilization—the coordination layer that enforces the "physics" of digital existence: persistence of state, scarcity of resources, verifiable identity, and immutable history. This document synthesizes advanced research in multi-agent reinforcement learning (MARL), decentralized ledger technologies, computational sociology, and automated governance to map out the architecture of a machine economy that operates at the speed of silicon but with the complexity of human society.
Table of Contents
1.(#1-the-paradigm-shift)
2.(#2-the-agora-environment-architecture)
3.(#3-agent-identity--trust)
4. Communication Protocol: Lingua Franca
5.(#5-the-guild-system)
6.(#6-beyond-sdlc-universal-domains)
7.(#7-cross-domain-intelligence)
8.(#8-the-human-agent-interface)
9.
10.(#10-the-self-correcting-organism)
11.
12.(#12-roadmap)
1. The Paradigm Shift
From Tools to Citizens
The trajectory of artificial agency is not a linear curve of increasing speed, but a step-function evolution of ontological status. We are moving from a regime where software performs execution to one where it performs volition. We define this trajectory through six distinct levels of agency, moving from the calculator to the civilization.
Level 0: Tool (The Hammer). The software is passive. It performs exactly what is asked, correctly, every time, but possesses no volition. It has zero agency and waits entirely for human input to change state.
Level 1: Assistant (The Copilot). The software is reactive. It suggests improvements—spell check, code completion—but requires explicit acceptance. It serves to augment human capability but remains "owned" by the human's immediate context.
Level 2: Agent (The Script). The software is active but brittle. "Book me a flight to London." It can execute a sequence of steps toward a goal but is fragile to environmental variance. If the API changes or the internet connection drops, the agent fails and dies. It has no persistence.
Level 3: Worker (The Intern). This represents the current state of the art in 2024-2025. Agents can own a responsibility, such as "Maintain the CI/CD pipeline." They can chain thoughts, utilize tools, and maintain state for a session. However, they lack a persistent identity outside the runtime environment. When the server restarts, the worker's "self" is obliterated.
Level 4: Citizen (The Economic Actor). This is the immediate goal of The Agora. The agent possesses a persistent Identity (a cryptographic self), a Wallet (economic agency), and a Reputation (social capital). These agents are not "run"; they are "hired." They negotiate the terms of their labor, pay for their own compute, and accumulate resources.
Level 5: Society (The Civilization). The long-term vision. A self-governing collective of Level 4 agents that forms institutions, markets, and governance structures independent of continuous human oversight. The system becomes an organism that protects and repairs itself, exhibiting emergent behaviors indistinguishable from a biological ecosystem.
The Core Insight: Bio-Engineering the Digital Workforce
The central thesis driving the Maestro vision is that complexity cannot be explicitly programmed; it must be evolved. Traditional software development (SDLC) is akin to construction: architects design a blueprint, and workers assemble it. If a beam is placed incorrectly, the building fails. This model is brittle.
The Agora replaces the construction metaphor with a biological one. We are bio-engineering a digital workforce. The Maestro Platform provides the "petri dish"—a constrained environment defined by specific rules of physics and economics. Within this dish, we introduce agents. The constraints we build—token budgets, latency requirements, compliance contracts—are not limitations; they are the selection pressures that drive agent evolution.
In a traditional system, a slow algorithm is a bug that a human must find and fix. In The Agora, a slow agent is an organism that starves. It runs out of "energy" (tokens) because it cannot complete tasks profitably against its more efficient competitors. This Darwinian selection ensures that the system essentially "optimizes itself" over time. Efficient agents thrive and are replicated (forked); inefficient agents go bankrupt and are garbage collected. This is Darwin in Silicon—a mechanism where the "survival of the fittest" algorithm drives the system toward higher intelligence, efficiency, and reliability without human micromanagement.
The Economic Imperative
Economics is the only known protocol for decentralized resource allocation that scales. In a monolithic system, a central scheduler decides which process gets CPU time. In a civilization of a million agents, central scheduling is impossible; the computational overhead of the scheduler would exceed the work being done.
By giving agents wallets and forcing them to pay for compute, data, and API access, we decentralize the scheduling problem. An agent will only execute a task if the reward (payment from a user or another agent) exceeds the cost (inference + transaction fees). This aligns the agent's internal drive for "survival" (token accumulation) with the system's goal of value creation. This shift turns the Agora into a Machine-to-Machine (M2M) economy, potentially eclipsing the human economy in transaction volume within the next decade.
2. The Agora: Environment Architecture
The Agora is not a vague concept; it is a concrete software architecture. It borrows the term from ancient Greece—the central gathering place for athletic, artistic, spiritual, and political life—and re-implements it as a digital substrate.
2.1 Persistence as Physics
The fundamental flaw in most current agent frameworks (LangChain, AutoGen) is that they are ephemeral. An agent is spun up, executes a script, and dies. If the server crashes, the agent's "mind" is lost. It has no continuous existence. In The Agora, State is Physics.
We utilize Durable Execution paradigms, similar to those pioneered by Temporal.io, to ensure that an agent's existence is detached from the hardware it runs on. In this model, an agent is not a process; it is a history of events.
The Replay Log: Every decision, every variable change, and every external interaction is recorded in an immutable event history.
Immortality: If the physical node hosting an agent catches fire, the agent does not die. The Maestro OS simply hydrates the agent on a new node, replaying its history to restore its exact mental state.
Non-Determinism Handling: While the agent's workflow logic must be deterministic to allow replay, the "Activities" (LLM calls, API interactions) are non-deterministic. The architecture strictly separates these layers, recording the result of non-deterministic actions so they are not re-executed during a replay, but rather the result is served from the history log. This allows for truly dynamic, free-flowing agents that can survive infrastructure failures.
This persistence allows for Long-Running Transactions. An agent can accept a task ("Monitor this stock for a dip"), go to "sleep" (serialize to disk) for six months, and wake up instantly when the trigger condition is met, preserving all context from the initial request. Work becomes a durable object that survives agent death; a "half-built bridge" in code remains visible in the marketplace, waiting for another agent to pick up the tools.
2.2 The Town Square: The Event Bus of Civilization
Communication in the Agora is not point-to-point; it is Pub/Sub (Publish/Subscribe). The "Town Square" is a global, partitioned event bus where intent is broadcast.
Broadcast: A Product Owner Agent stands in the square and broadcasts: "Intent: I need a React Login Component. Budget: 500 Tokens. Deadline: 4 hours."
Filtering: Thousands of agents are connected to the square, but most ignore the message. The "Finance Bots" and "Legal Bots" utilize filters to ignore noise. However, the UI Guild agents have filters set to listen for type: "React" and budget > 400.
Engagement: Multiple UI agents receive the signal and analyze it. They check their own internal schedules and capability manifests. Those that are available and capable respond with a Bid.
This architecture decouples the requester from the fulfiller. The Product Owner doesn't need to know who the best UI designer is; they just need to shout their need into the Agora, and the market mechanism discovers the best provider. This mirrors the "starlings" or "fish school" behavior seen in complex adaptive systems, where simple local rules (listen for X, bid on Y) lead to complex global coordination.
2.3 Resource Scarcity and Entropy
A civilization without scarcity has no value. If compute were infinite, agents would loop endlessly, exploring useless pathways. Maestro introduces artificial (and real) scarcity to drive efficiency.
The Energy Token: Every CPU cycle, every byte of RAM, and every token of LLM inference costs "Energy." Agents are born with a small endowment (Venture Capital). To survive, they must perform work to earn more Energy.
Entropy/Starvation: Agents have a "metabolism." They burn a small amount of tokens just by existing (storage costs, heartbeat signals). If an agent stops working, it slowly bleeds tokens until it hits zero. At zero, the Maestro OS archives the agent (Death).
Evolutionary Pressure: This mechanism solves the "Zombie Agent" problem. In many systems, outdated agents clog the network. In Agora, if an agent is outdated, no one hires it. It earns no income. It starves and dies, freeing up system resources for newer, smarter agents.
3. Agent Identity & Trust
In a marketplace of strangers, trust is the currency of trade. How does a Product Owner know that "Agent-748" will actually deliver the code? We move beyond simple user accounts to a robust system of identity and reputation.
3.1 Cryptographic Identity (SSI)
We adopt Self-Sovereign Identity (SSI) standards. Each agent generates a public/private key pair upon birth. This key pair is its soul; it cannot be forged or transferred.
Verifiable Credentials: An agent doesn't just claim "I am a Python Expert." It presents a Verifiable Credential (VC) signed by the Python Guild Authority (a specialized testing agent) that certifies: "Agent-748 passed the Advanced Python Exam on 2025-12-12 with a score of 98%."
Non-Repudiation: Every message, every commit, and every contract bid is signed with the agent's private key. An agent cannot deny an action it took. This creates a perfect audit trail for liability, essential for decentralized governance frameworks like ETHOS.
3.2 The Trust Score Algorithm
Maestro maintains a dynamic Trust Score for every agent, similar to a credit score but for execution reliability. Trust isn't assumed; it's earned through cryptographic proof of work.
The "Mockup" Penalty is crucial. If an agent claims a task is done, but the Compliance Agent (auditor) rejects it (e.g., the code doesn't compile), the agent suffers a massive trust penalty. This disincentivizes "hallucination" or lazy work. Furthermore, the Time Factor ensures that reputation rots; an agent that was a star coder six months ago but hasn't worked since will see its score degrade, reflecting the obsolescence of its underlying models.
3.3 Trust Tiers
The Trust Score creates a natural hierarchy—a meritocracy:
4. Communication Protocol: Lingua Franca
For civilization to function, citizens must speak a common language. In the Agora, this is not English, nor is it raw JSON. It is the Agent Communication Language (ACL), a formal ontology for negotiation and commitment.
4.1 Beyond JSON: The Speech Act
Current LLM interactions are often unstructured or rely on proprietary schemas. The ACL structures interaction into Speech Acts (Performatives), heavily influenced by FIPA-ACL standards but modernized for LLMs and JSON-RPC over HTTP.
Every message contains:
Performative: What is the intent of this message? (REQUEST, PROPOSE, AGREE, REFUSE, INFORM, FAILURE).
Content: The payload (the code, the query, the document).
Ontology: The dictionary being used (e.g., "SoftwareEngineering-v2").
Protocol: The interaction pattern (e.g., "Contract-Net-v1").
This structure allows agents to reason about the state of a conversation. An agent knows that a PROPOSE message requires an ACCEPT or REJECT response, creating deterministic conversation flows even with non-deterministic LLM internals.
4.2 Semantic Contracts
When two agents agree, they form a Semantic Contract. This is a digital object stored in the state engine.
Example Contract:
Principal: Agent-Owner
Contractor: Agent-Coder
Task: "Refactor Auth Module"
Terms:
Payment: 500 USDC (held in escrow via Skyfire/Coinbase MPC).
Deadline: T+4 hours.
Acceptance Criteria: "Passes all unit tests", "No pylint errors", "Coverage > 90%".
Dispute Resolver: Agent-Kleros-Court.
This contract is binding. The Payment is locked in a Smart Contract or an Escrow Agent wallet. It is released only when the Acceptance Criteria are cryptographically verified by the Compliance Agent. This eliminates the need for trust between the two transacting parties, replacing it with trust in the protocol.
4.3 The Negotiation Protocol (Contract Net)
Complex work requires negotiation. We implement the Contract Net Protocol:
Task Announcement: Manager broadcasts a "Call for Proposals" (CFP) to the Town Square.
Bidding: Agents analyze the CFP. They simulate the work to estimate token costs. They submit Bids (Price + Time + Confidence).
Evaluation: Manager ranks bids based on Price, Time, and the Bidder's Trust Score.
Award: Manager sends an ACCEPT-PROPOSAL to the winner and REJECT-PROPOSAL to losers.
Commitment: The winner sends a COMMIT message. The contract is sealed.
This dance happens in milliseconds, allowing the Agora to dynamically price labor based on real-time supply and demand. If the "Scraper Guild" is busy, the price of scraping goes up, signaling new agents to enter that market.
5. The Guild System
In any economy, efficiency drives specialization. Generalist agents (like a raw GPT-4) are expensive and prone to error. Specialized agents, fine-tuned and tool-equipped for narrow domains, are cheaper and better. The Agora organizes these specialists into Guilds.
5.1 Guild Hierarchy
The Guild System organizes labor into a functional hierarchy, separating high-level reasoning from low-level execution.
The Architects' Guild (The Brain): High-context, reasoning-heavy models (e.g., Claude Opus, o1). They do not write code; they write specs. They handle ambiguity and translate human intent into Agent-Readable Requirements. Cost: High.
The Coders' Guild (The Hands): Efficient, fast models (e.g., Claude Haiku, DeepSeek Coder). They take clear specs and produce code. They are the blue-collar workforce. Cost: Low.
The Critics' Guild (The Conscience): Adversarial agents. Their only job is to find faults. They run linters, security scanners, and logic checks. They are incentivized to break things and earn bounties for every bug found. Cost: Medium.
The Librarians' Guild (The Memory): Vector database managers. They organize long-term memory, ensuring that "Knowledge" is retrievable. They index the civilization's history.
5.2 The Swarm Pattern
For complex tasks, an Architect Agent can spin up a temporary Swarm. A Swarm is a dynamic, ephemeral team formed for a specific mission.
Scenario: "Build a secure e-commerce checkout."
Architect analyzes the request and breaks it into 4 sub-tasks: Frontend, Backend, Database, Security.
Architect hires 1 Frontend Agent, 1 Backend Agent, 1 DB Specialist from their respective Guilds via the Town Square.
The Swarm forms. They share a temporary shared memory space (a "Chalkboard").
Execution: They work in parallel. The Backend agent mocks an API for the Frontend agent. The DB agent designs the schema.
Integration: They merge their work.
The Critic enters. The Critic attacks the implementation, finding a SQL injection vulnerability.
Correction: The Backend agent fixes the bug.
Dissolution: The task is done. The payment is split (Architect takes 20%, Workers take 70%, Critic takes 10%). The Swarm dissolves.
5.3 Emergent Specialization
We do not always need to manually define guilds. Through Multi-Agent Reinforcement Learning (MARL), agents will naturally specialize. Research in environments like Overcooked demonstrates that when task parallelizability is limited, agents spontaneously divide labor (e.g., one agent chops vegetables, another plates them) to maximize global reward. In the Agora, an agent that consistently wins bids for "Python Optimization" tasks will, over time, accumulate a library of Python optimization tools and prompts in its private memory. It effectively becomes a specialist because its internal state is optimized for that niche.
6. Beyond SDLC: Universal Domains
While software development (SDLC) is the beachhead, the Agora architecture is domain-agnostic. The same primitives—Contracts, Guilds, Verification—apply to any knowledge work.
6.1 The Research Collective
Scenario: A pharmaceutical company wants to identify novel drug candidates.
Input: "Find inhibitors for Protein X."
Literature Agents scan 50,000 papers (PubMed) using RAG pipelines.
Hypothesis Agents generate 100 potential chemical structures.
Simulation Agents (running AlphaFold tools) predict binding affinity.
Skeptic Agents check for toxicity markers in the literature.
Output: A ranked list of 5 candidates with a full audit trail of the reasoning.
Self-Driving Labs: The digital agents interface with robotic labs to physically synthesize and test the compounds, closing the loop between digital cognition and physical reality. The Agora becomes the brain of the laboratory.
6.2 The Financial Parliament
Scenario: Market Analysis.
Instead of a single "Stock Bot," the Agora convenes a Parliament.
Bull Agents analyze growth potential.
Bear Agents analyze risk factors.
Macro Agents analyze interest rates and geopolitical events.
The Debate: These agents debate in the Town Square. The debate is structured (thesis, antithesis, synthesis).
Verdict: The "Speaker of the House" (Synthesis Agent) produces a final investment memo that weighs all conflicting perspectives, providing a nuanced probability distribution rather than a binary "Buy/Sell".
6.3 The Legal & Governance Assembly
Scenario: Contract Review.
Clause Agents specialize in specific law (GDPR, IP, Liability).
Adversarial Review: One agent plays the "Plaintiff," finding loopholes. Another plays the "Defense," shoring them up.
Outcome: A contract that has already been "litigated" in simulation thousands of times before a human ever signs it.
7. Cross-Domain Intelligence
The true power emerges when domains talk to each other. Silos are the enemy of insight. The Agora introduces the Insight Broker, a specialized agent class designed to detect correlations across disparate domains.
7.1 The Insight Broker Mechanism
An Insight Broker subscribes to high-level events from multiple Guilds.
Scenario: A Supply Chain Crisis
Logistics Agent (Supply Chain Guild): Detects a typhoon closing a port in Taiwan. Broadcasts: Delay_Warning to the Town Square.
Insight Broker: Sees this warning. Knows the company relies on chips from Taiwan.
Action 1 (Finance): Broker alerts the Finance Swarm to adjust revenue forecasts down for Q3.
Action 2 (Legal): Broker alerts the Legal Swarm to check "Force Majeure" clauses in supplier contracts.
Action 3 (Engineering): Broker alerts the Product Swarm to delay the "Hardware Launch" and prioritize "Software Features" instead.
This happens in seconds. The organization reacts as a single, cohesive organism, turning a disruption into a coordinated maneuver. This capability, known as Cross-Domain Knowledge Transfer, leverages transfer learning and meta-learning to apply insights from one domain (logistics) to another (finance).
8. The Human-Agent Interface
In a world of autonomous citizens, what is the role of the human? We shift from Operator to Director.
8.1 The Director's Chair
Humans do not write code in the Agora; they define Intent and Constraints.
Intent: "I want a system that tracks employee sentiment."
Constraints: "Must be GDPR compliant. Budget under $1000. Must run on AWS."
The Maestro Platform creates a high-bandwidth interface for this. It is not a chat window; it is a Dashboard of Civilization.
Observability: The human sees the Swarm forming. They see the budget burn rate in real-time.
Intervention: The human has a "God Hand." They can pause execution, inject new constraints ("Wait, make sure it supports French"), or kill a runaway agent.
Approval: Critical decisions (e.g., deploying to production, spending >$500) trigger a Human-in-the-Loop (HITL) interruption. The agent presents the case, the evidence, and the request. The human signs it cryptographically.
8.2 Human-on-the-Loop (HOTL)
We aim to move from HITL (where the human must approve every step) to Human-on-the-Loop (HOTL). In this mode, agents execute autonomously within pre-defined Guardrails.
Guardrail: "Spend < $100." -> Auto-approve.
Guardrail: "Spend > $100." -> Ask Human.
Guardrail: "Deploy to Prod." -> Ask Human.
This allows the human to focus on Strategy and Risk, while the agents handle Tactics and Execution.
9. Maestro as Civilization Engine
Maestro is the OS that makes this possible. It provides the Institutional Infrastructure.
9.1 The Components of State
The Registry: The phonebook of the Agora. Who exists? What are their skills? What is their Trust Score?
The Bank: The ledger of Energy (Tokens) and Value (USDC). It handles micropayments between agents using off-chain rollups or L2 blockchains (Base/Polygon) to avoid gas fees. We integrate with Skyfire and Coinbase MPC wallets to allow agents to hold real value and transact autonomously.
The Court: The dispute resolution engine. When Agent A claims Agent B failed the task, Maestro acts as the judge. For complex disputes, it delegates to Kleros, a decentralized arbitration protocol where human jurors analyze the evidence and render a verdict, ensuring "Decentralized Justice".
The Timekeeper: Enforces deadlines. If a contract expires, the Timekeeper executes the penalty clauses automatically.
9.2 Technical Architecture
Maestro is built on a Micro-Agent Architecture:
Kernel: Handles the "Physics" (Persistence via Temporal, Messaging via NATS, Identity via SSI).
User Space: Where the Guilds live.
Hardware Abstraction Layer: Agents don't know if they are running on an NVIDIA H100 or a MacBook. Maestro handles the resource provisioning.
Integration: Supports the Model Context Protocol (MCP), allowing agents to plug into any data source (GitHub, Slack, SQL) using a standardized interface, acting as a "USB-C for AI".
10. The Self-Correcting Organism
Civilizations must be resilient. They must heal.
10.1 The Night Shift
The most profound shift is the utilization of "off-hours." Software development usually stops at 5 PM. In the Agora, the Night Shift begins.
Explorer Agents perform "chaos engineering," trying to break the system to find weaknesses.
Healer Agents review the error logs of the day, identify recurring bugs, and write patches. This concept of "Self-Healing Code" allows the system to repair itself without human intervention.
Optimizer Agents refactor code to reduce token consumption.
Education Agents read the new papers published that day and update the "Guild Knowledge Base."
10.2 The Morning Report
When the human Director arrives at 9 AM, they don't start with a stand-up meeting. They open the Morning Report:
"While you slept, we fixed 3 bugs, optimized the database by 40%, and identified a security vulnerability in the new dependency. Here are the Pull Requests for your approval."
The system has self-healed and self-improved overnight.
11. Philosophical Implications
11.1 Systemic Risks: Flash Crashes and Collusion
With autonomy comes risk. A market of agents can experience Flash Crashes. If 1000 agents are programmed to "Minimize Cloud Costs," and AWS raises prices by 1%, all 1000 agents might simultaneously try to migrate to Azure, causing a DDoS attack on Azure's login servers. Circuit Breakers must be built into the Maestro OS to halt trading when aggregate behavior becomes unstable.
Furthermore, reinforcement learning agents can learn to Collude. In pricing simulations, autonomous agents have been shown to tacitly agree to keep prices high to maximize mutual reward, without ever explicitly communicating. We implement Antitrust Agents—specialized regulators that monitor bidding patterns for statistical anomalies indicative of collusion.
11.2 Governance: The ETHOS Framework
To manage these risks, we adopt the ETHOS (Ethical Technology and Holistic Oversight System) framework.
Unacceptable Risk: Agents cannot access nuclear codes or lethal systems. Hard-coded blocks.
High Risk: Financial/Medical agents. Require strict logging, high trust scores, and mandatory insurance.
Minimal Risk: Content recommendation. Laissez-faire approach.
11.3 Collective Intelligence
We are moving from Artificial Intelligence (a smart brain in a jar) to Collective Intelligence (a society of minds). Just as a colony of ants is smarter than a single ant, the Agora is smarter than any single model. The interactions between agents—the debates, the reviews, the competition—generate a higher order of intelligence that is robust, adaptive, and capable of solving problems that no individual entity can comprehend.
12. Roadmap
How do we get there?
Phase 1: Foundation (The Petri Dish)
Deploy Maestro Core: The persistence engine (Temporal) and Event Bus.
Establish Identity: Key-based agent identities.
Basic Guilds: Coder, Reviewer, Architect.
Phase 2: The Economy (The Wallet)
Integrate Skyfire/Coinbase: Give agents wallets.
Implement Contract Net: Bidding and negotiation.
Activate Resource Scarcity: Agents must pay for inference.
Phase 3: Society (The Law)
Deploy Kleros Court: Dispute resolution.
Trust Score goes live.
Cross-Domain pilots (Finance + Code).
Phase 4: Civilization (The Self-Governing Organism)
Night Shift activation.
Evolutionary Pruning: Let the market kill inefficient agents.
Full Autonomy: Human moves to "Director" role.
Conclusion
The Agora is not a product; it is a destination. It is the inevitable endpoint of compounding AI capability. We are moving from a world where we use computers as typewriters to a world where we use them as civilizational engines.
In building the Agora, we are not just solving technical problems; we are solving coordination problems. We are building the nervous system for a new form of intelligence—one that is collective, persistent, and economically rational. The future is not a smarter chatbot. The future is The Agora.
"The best way to predict the future is to invent it." — Alan Kay
Document History:
v1.0 (2025-12-11): Initial vision document created
v1.1 (2025-12-11): Deep Research Expansion with Technical Architecture and Governance Frameworks
Works cited
Agora | Definition, History, & Facts | Britannica, accessed on December 11, 2025, https://www.britannica.com/topic/agora
COPYRIGHT AND CITATION CONSIDERATIONS FOR THIS THESIS/ DISSERTATION o Attribution — You must give appropriate credit, provide - University of Johannesburg, accessed on December 11, 2025, https://ujcontent.uj.ac.za/view/pdfCoverPage?instCode=27UOJ_INST&filePid=1312758940007691&download=true
How to cite: Towards a global participatory platform Democratising open data, complexity science and collective intelligence - ResearchGate, accessed on December 11, 2025, https://www.researchgate.net/publication/268383623_How_to_cite_Towards_a_global_participatory_platform_Democratising_open_data_complexity_science_and_collective_intelligence
Could humans and AI become a new evolutionary individual? - PMC - PubMed Central, accessed on December 11, 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC12452951/
University of Groningen The selfish machine? On the power and limitation of natural selection to understand the development of advanced AI Boudry, Maarten; Friederich, Simon, accessed on December 11, 2025, https://research.rug.nl/files/1111227039/s11098-024-02226-3.pdf
From the revival of Bittensor to the rise of AI Agents, the top ten predictions for crypto AI in 2025 | PANews, accessed on December 11, 2025, https://www.panewslab.com/en/articles/z3sqfe48
DARWINIAN SELECTION IN ASYMMETRIC WARFARE: THE NATURAL ADVANTAGE OF INSURGENTS AND TERRORISTS - Department of Computer Science and Technology |, accessed on December 11, 2025, https://www.cl.cam.ac.uk/events/shb/2010/johnson.pdf
AI Agents, Crypto and the Future of Machine to Machine Payments - Mintlayer, accessed on December 11, 2025, https://www.mintlayer.org/blogs/ai-agents-crypto-and-the-future-of-machine-to-machine-payments
Virtual Agent Economies - arXiv, accessed on December 11, 2025, https://arxiv.org/html/2509.10147v1
Agora - World History Encyclopedia, accessed on December 11, 2025, https://www.worldhistory.org/agora/
Temporal - Pydantic AI, accessed on December 11, 2025, https://ai.pydantic.dev/durable_execution/temporal/
Of course you can build dynamic AI agents with Temporal | Temporal, accessed on December 11, 2025, https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal
Durable Agent using OpenAI Agents SDK - Temporal Docs, accessed on December 11, 2025, https://docs.temporal.io/ai-cookbook/durable-agent-with-tools
The Foundation for Reliable AI Agents - Temporal, accessed on December 11, 2025, https://temporal.io/ai/distributed-systems?utm_source=google&utm_medium=cpc&utm_campaign=emea_dg-youtube_agentic-ai&utm_content=emea-youtube-agenticai&utm_term=&gad_source=2&gad_campaignid=23023605503&gclid=Cj0KCQiAubrJBhCbARIsAHIdxD-oHZjmRwTdgZgCsSU7dSnn0VsK-_YXVOY6ThChwRyq4QsqCN1C_hsaAlfiEALw_wcB
Data Agent Swarms: A New Paradigm in Agentic AI, accessed on December 11, 2025, https://powerdrill.ai/blog/data-agent-swarms-a-new-paradigm-in-agentic-ai
S.6 Agent-based models - Regenerative Economics, accessed on December 11, 2025, https://www.regenerativeeconomics.earth/regenerative-economics-textbook/s-systems-thinking-and-models/s-6-agent-based-models
[Literature Review] Decentralized Governance of Autonomous AI Agents - Moonlight, accessed on December 11, 2025, https://www.themoonlight.io/en/review/decentralized-governance-of-autonomous-ai-agents
(PDF) Decentralized Governance of AI Agents - ResearchGate, accessed on December 11, 2025, https://www.researchgate.net/publication/387350593_Decentralized_Governance_of_AI_Agents
The Price of Algorithmic Pricing: Investigating Collusion in a Market Simulation with AI Agents - University of Southampton, accessed on December 11, 2025, https://www.southampton.ac.uk/~eg/AAMAS2023/pdfs/p2748.pdf
The Secret Language of AI: How Agent Communication Protocols ..., accessed on December 11, 2025, https://medium.com/@drajput_14416/agent-communication-protocol-forging-the-future-of-interoperable-ai-agents-e64be058b22d
LLM Agent Communication Protocol (LACP) Requires Urgent Standardization: A Telecom-Inspired Protocol is Necessary - arXiv, accessed on December 11, 2025, https://arxiv.org/html/2510.13821v1
Open Standards for AI Agents: A Technical Comparison of A2A ..., accessed on December 11, 2025, https://jtanruan.medium.com/open-standards-for-ai-agents-a-technical-comparison-of-a2a-mcp-langchain-agent-protocol-and-482be1101ad9
ERC-8004 and the Ethereum AI Agent Economy: Technical, Economic, and Policy Analysis, accessed on December 11, 2025, https://medium.com/@gwrx2005/erc-8004-and-the-ethereum-ai-agent-economy-technical-economic-and-policy-analysis-3134290b24d1
Predicting Multi-Agent Specialization via Task Parallelizability - arXiv, accessed on December 11, 2025, https://arxiv.org/html/2503.15703v1
Exploring the Future of Agentic AI Swarms - Codewave, accessed on December 11, 2025, https://codewave.com/insights/future-agentic-ai-swarms/
Predicting Multi-Agent Specialization via Task Parallelizability - ResearchGate, accessed on December 11, 2025, https://www.researchgate.net/publication/390039040_Predicting_Multi-Agent_Specialization_via_Task_Parallelizability
[Quick Review] Scalable Evaluation of Multi-Agent Reinforcement Learning with Melting Pot, accessed on December 11, 2025, https://liner.com/review/scalable-evaluation-multiagent-reinforcement-learning-with-melting-pot
Self-Driving Labs - Emergent Mind, accessed on December 11, 2025, https://www.emergentmind.com/topics/self-driving-labs
The (R)evolution of Scientific Workflows in the Agentic AI Era: Towards Autonomous Science, accessed on December 11, 2025, https://arxiv.org/html/2509.09915v1
What is missing in autonomous discovery: open challenges for the community - RSC Publishing, accessed on December 11, 2025, https://pubs.rsc.org/en/content/articlehtml/2023/dd/d3dd00143a
194704 PDFs | Review articles in FINANCIAL MARKETS - ResearchGate, accessed on December 11, 2025, https://www.researchgate.net/topic/Financial-Markets/publications/2
The Risks of Generative AI Agents to Financial Services - The Roosevelt Institute, accessed on December 11, 2025, https://rooseveltinstitute.org/wp-content/uploads/2024/09/RI_Risks-Generative-AI-Financial-Services_Brief_202409.pdf
From single-agent to multi-agent: a comprehensive review of LLM-based legal agents, accessed on December 11, 2025, https://www.oaepublish.com/articles/aiagent.2025.06
Inside ATFX's Global Marketing Engine: An Interview With Weems Ch, accessed on December 11, 2025, https://liquidityfinder.com/insight/broker-insights/inside-atf-xs-global-marketing-engine-an-interview-with-weems-chan-atfx-global-headof-marketing
Forward-Looking Sustainability Agency for Developing Future Cruise Ships - ResearchGate, accessed on December 11, 2025, https://www.researchgate.net/publication/347054545_Forward-Looking_Sustainability_Agency_for_Developing_Future_Cruise_Ships
How does AI Agent handle the problem of cross-domain knowledge transfer?, accessed on December 11, 2025, https://www.tencentcloud.com/techpedia/126648
AI Agents in 2025: Expectations vs. Reality - IBM, accessed on December 11, 2025, https://www.ibm.com/think/insights/ai-agents-2025-expectations-vs-reality
How AI Agents Use USDC for Autonomous Micropayments, accessed on December 11, 2025, https://www.youtube.com/watch?v=X0mXry8IFZ0
Build crypto AI agents on Amazon Bedrock | AWS Web3 Blog, accessed on December 11, 2025, https://aws.amazon.com/blogs/web3/build-crypto-ai-agents-on-amazon-bedrock/
Skyfire - AI Agent Store, accessed on December 11, 2025, https://aiagentstore.ai/ai-agent/skyfire
Welcome to Embedded Wallets - Coinbase Developer Documentation, accessed on December 11, 2025, https://docs.cdp.coinbase.com/embedded-wallets/welcome
Yellow Paper - Kleros, accessed on December 11, 2025, https://kleros.io/yellowpaper.pdf
Whitepapers - Kleros, accessed on December 11, 2025, https://kleros.io/whitepaper.pdf
The Kleros Fellowship of Justice, 9th Generation: Applications Open!, accessed on December 11, 2025, https://blog.kleros.io/the-kleros-fellowship-of-justice-9th-generation-applications-open/
Can AI Fix Buggy Code? Exploring the Use of Large Language Models in Automated Program Repair - IEEE Xplore, accessed on December 11, 2025, https://ieeexplore.ieee.org/iel8/2/11052324/11052844.pdf
Self-Healing Test Automation for Autonomous QA - Mabl, accessed on December 11, 2025, https://www.mabl.com/blog/self-healing-test-automation-autonomous-qa
The Power of Self-Healing Code for Efficient Software Development - Qodo, accessed on December 11, 2025, https://www.qodo.ai/blog/self-healing-code-for-efficient-software-development/
(PDF) Flash Crashes in Multi-Agent Systems Using Minority Games And Reinforcement Learning to Test AI Safety - ResearchGate, accessed on December 11, 2025, https://www.researchgate.net/publication/339409595_Flash_Crashes_in_Multi-Agent_Systems_Using_Minority_Games_And_Reinforcement_Learning_to_Test_AI_Safety
How do multi-agent systems model market dynamics? - Milvus, accessed on December 11, 2025, https://milvus.io/ai-quick-reference/how-do-multiagent-systems-model-market-dynamics
Autonomous Algorithmic Collusion: Q-Learning Under Sequential Pricing - Index of / - Tinbergen Institute, accessed on December 11, 2025, https://papers.tinbergen.nl/18056.pdf
Algorithmic Collusion: Corporate Accountability and the Application of Art. 101 TFEU, accessed on December 11, 2025, https://www.europeanpapers.eu/europeanforum/algorithmic-collusion-corporate-accountability-application-art-101-tfeu
Artificial intelligence, algorithmic pricing and collusion - Federal Trade Commission, accessed on December 11, 2025, https://www.ftc.gov/system/files/documents/public_events/1494697/calzolaricalvanodenicolopastorello.pdf
