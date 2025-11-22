# Autonomous Agent Discussions

**TRUE autonomous multi-agent collaboration** - No hardcoded conversations!

## What's Different?

### ❌ Previous Examples (Scripted)
```python
# Hardcoded conversation
await doctor.send_message("nurse", "Check patient vitals")
await nurse.send_message("doctor", "BP is 120/80")
```

### ✅ Autonomous Examples (Real AI)
```python
# Just give agenda and let agents talk autonomously
await run_autonomous_discussion(
    agenda="Discuss patient treatment plan",
    discussion_rounds=3,
    team_composition=[doctor_config, nurse_config]
)
# Agents use Claude to decide what to say and actually use MCP tools!
```

## How It Works

### 1. You Provide:
- **Agenda** - What to discuss
- **Rounds** - How many discussion iterations
- **Target** - Desired outcome (optional)
- **Team** - Who participates with their expertise

### 2. Agents Autonomously:
- ✅ Use Claude to understand the agenda
- ✅ Check messages from other agents
- ✅ Decide what to contribute
- ✅ Post messages via MCP tools
- ✅ Share knowledge
- ✅ Propose and vote on decisions
- ✅ Build on each other's ideas

### 3. Result:
Real, unscripted AI-to-AI collaboration!

---

## Quick Start

### Method 1: Python Code

```python
from autonomous_discussion import run_autonomous_discussion

await run_autonomous_discussion(
    agenda="Design a new feature for real-time collaboration",
    discussion_rounds=4,
    target_outcome="Agreed design with technical approach",
    team_composition=[
        {
            'id': 'pm',
            'role': 'Product Manager',
            'expertise': 'User needs, requirements'
        },
        {
            'id': 'engineer',
            'role': 'Engineer',
            'expertise': 'Technical implementation'
        }
    ]
)
```

### Method 2: Config File (No Coding!)

**1. Edit `autonomous_config.yaml`:**
```yaml
discussion:
  agenda: "Plan Q4 product roadmap"
  rounds: 4
  target_outcome: "Prioritized feature list with timeline"

  team:
    - id: "product_lead"
      role: "Product Lead"
      expertise: "Product strategy, market analysis"

    - id: "eng_manager"
      role: "Engineering Manager"
      expertise: "Technical feasibility, team capacity"
```

**2. Run it:**
```bash
python run_autonomous_discussion.py autonomous_config.yaml
```

---

## Built-in Examples

### Example 1: Product Feature Discussion
```bash
python autonomous_discussion.py 1
```

**Team:** PM, Tech Lead, UX Designer, Engineer (4 members)
**Agenda:** Design new real-time collaboration feature
**Rounds:** 4

### Example 2: Research Problem
```bash
python autonomous_discussion.py 2
```

**Team:** PI, ML Researcher, Medical Doctor (3 members)
**Agenda:** Improve ML model accuracy for disease prediction
**Rounds:** 3

### Example 3: Crisis Response
```bash
python autonomous_discussion.py 3
```

**Team:** Incident Commander, Hazmat, Fire Chief, EMS, Public Info (5 members)
**Agenda:** Coordinate chemical spill response
**Rounds:** 5

### Example 4: Small Team
```bash
python autonomous_discussion.py 4
```

**Team:** Doctor, Pharmacist (2 members)
**Agenda:** Review patient treatment plan
**Rounds:** 3

---

## How Agents Autonomously Communicate

### Agent System Prompt (Excerpt)
```
You are {agent_id}, participating in a team discussion.

AVAILABLE TOOLS (use them proactively):
1. post_message - Send messages to team members
2. get_messages - Check messages from others
3. share_knowledge - Share insights and data
4. propose_decision - Propose decisions
5. vote_decision - Vote on proposals

PARTICIPATION GUIDELINES:
1. Check messages from other team members
2. Contribute your expertise
3. Build on others' ideas
4. Propose decisions when appropriate

IMPORTANT: Use the MCP tools to actually communicate!
```

### What Happens Each Round

For each discussion round, each agent gets:
```
DISCUSSION ROUND {N}/{TOTAL}

AGENDA: {agenda}
YOUR ROLE: {role}
YOUR EXPERTISE: {expertise}

INSTRUCTIONS:
1. Check messages from other team members (get_messages)
2. Read and consider what others have said
3. Contribute based on your expertise
4. Use tools: post_message, share_knowledge, propose_decision, vote_decision
5. Build on what others have shared

Actually USE the coordination tools to communicate!
```

Then Claude autonomously decides:
- What to say
- Who to message
- What knowledge to share
- Whether to propose decisions
- How to vote

---

## Sample Output

```
🤖 AUTONOMOUS AGENT DISCUSSION
======================================================================

📋 AGENDA: Design a new real-time collaboration feature
🔄 ROUNDS: 4
🎯 TARGET: Agreed design with technical approach

======================================================================

👥 TEAM MEMBERS:

   ✓ product_manager: Product Manager (User needs, market requirements)
   ✓ tech_lead: Technical Lead (System architecture, feasibility)
   ✓ ux_designer: UX Designer (User experience, interaction design)
   ✓ engineer: Senior Engineer (Implementation, performance)

======================================================================

🎬 STARTING AUTONOMOUS DISCUSSION...

(Agents will autonomously use MCP tools to communicate)

======================================================================

[Agents have real AI-driven conversations here using MCP tools]

======================================================================

📊 DISCUSSION SUMMARY:

Team Participation:
  - Total messages: 23
  - Knowledge shared: 7
  - Decisions proposed: 2
  - Discussion rounds: 4

💬 Message Activity:
  - Average per round: 5.8
  - Average per agent: 5.8

🧠 Knowledge Sharing:
  - Items shared: 7
  - Collaboration level: High

🗳️ Decision Making:
  - Decisions proposed: 2
  - Team reached conclusions: Yes

======================================================================

✅ Autonomous discussion completed!
```

---

## Creating Custom Discussions

### Using YAML Config

Create `my_discussion.yaml`:
```yaml
discussion:
  agenda: "Your discussion topic here"
  rounds: 3
  target_outcome: "What you want to achieve"

  team:
    - id: "agent_1"
      role: "Role Name"
      expertise: "What they're good at"

    - id: "agent_2"
      role: "Another Role"
      expertise: "Their specialty"
```

Run it:
```bash
python run_autonomous_discussion.py my_discussion.yaml
```

### Using Python

```python
import asyncio
from autonomous_discussion import run_autonomous_discussion

async def my_discussion():
    await run_autonomous_discussion(
        agenda="Your agenda",
        discussion_rounds=3,
        target_outcome="Your target",
        team_composition=[
            {'id': 'agent1', 'role': 'Role', 'expertise': 'Skills'},
            {'id': 'agent2', 'role': 'Role', 'expertise': 'Skills'},
        ]
    )

asyncio.run(my_discussion())
```

---

## Key Differences from Scripted Examples

| Aspect | Scripted (domain_teams/) | Autonomous (this) |
|--------|-------------------------|-------------------|
| **Conversation** | Hardcoded | AI-generated |
| **Tool Usage** | Manual `send_message()` | Claude calls MCP tools |
| **Flow** | Predetermined | Dynamic |
| **Responses** | Scripted | Based on context |
| **Collaboration** | Simulated | Real |
| **Variability** | Same every time | Different each run |

---

## Use Cases

### Product Development
- Feature brainstorming
- Technical design reviews
- Roadmap planning
- Sprint retrospectives

### Research & Science
- Hypothesis development
- Experimental design
- Data interpretation
- Literature review discussions

### Healthcare
- Case consultations
- Treatment planning
- Grand rounds discussions
- Protocol development

### Business Strategy
- Go-to-market planning
- Competitive analysis
- Investment decisions
- Crisis management

### Education
- Curriculum design
- Teaching strategies
- Student assessment
- Program evaluation

---

## Tips for Better Autonomous Discussions

### 1. Clear Agenda
❌ "Discuss the product"
✅ "Design a real-time collaboration feature with technical architecture"

### 2. Right Number of Rounds
- **2-3 rounds:** Simple decisions, small teams
- **4-5 rounds:** Complex topics, medium teams
- **6-8 rounds:** Major decisions, large teams

### 3. Diverse Expertise
- Include complementary skills
- Balance technical and domain experts
- Add different perspectives

### 4. Specific Target Outcome
❌ "Make a decision"
✅ "Agreed technical design with implementation timeline and resource needs"

### 5. Team Size
- **2-3 agents:** Focused, efficient
- **4-5 agents:** Balanced perspectives
- **6-8 agents:** Comprehensive, complex

---

## Advanced: Monitoring Discussions

### Track Progress
```python
# During discussion
state = await coordinator.get_workspace_state()

print(f"Messages so far: {state['messages']}")
print(f"Knowledge shared: {state['knowledge_items']}")
print(f"Decisions: {state['decisions']}")
```

### Extract Decisions
```python
# After discussion
workspace = coordinator.shared_workspace

for decision in workspace['decisions']:
    print(f"Decision: {decision['decision']}")
    print(f"Proposed by: {decision['proposed_by']}")
    print(f"Votes: {decision['votes']}")
```

### Get Knowledge Base
```python
# Retrieve shared knowledge
for key, knowledge in workspace['knowledge'].items():
    print(f"{key}: {knowledge['value']}")
    print(f"  Category: {knowledge['category']}")
    print(f"  From: {knowledge['from']}")
```

---

## Troubleshooting

### Agents Not Communicating
**Check:** Are they using the MCP tools?
- Look for tool usage in Claude responses
- Increase rounds if discussion is too short
- Make agenda more specific

### Low Message Count
**Solutions:**
- Make rounds longer (add more rounds)
- Give more specific roles/expertise
- Add more controversial or complex topics

### No Decisions Reached
**Solutions:**
- Add explicit target outcome
- Increase discussion rounds
- Include decision-making role (coordinator, lead)

---

## Files

- `autonomous_discussion.py` - Main autonomous discussion engine
- `run_autonomous_discussion.py` - Config file runner
- `autonomous_config.yaml` - Example configuration
- `AUTONOMOUS_README.md` - This documentation

---

## What's Next?

Try these experiments:

1. **Same Agenda, Different Teams**
   - Run same agenda with 2, 4, 8 agents
   - Compare outcomes

2. **Same Team, Different Agendas**
   - Test team on various topics
   - See how expertise applies

3. **Iterative Discussions**
   - Take output from one discussion
   - Use as input for next discussion
   - Build on previous decisions

4. **Cross-Domain Teams**
   - Mix experts from different fields
   - Foster innovation through diversity

---

**Ready to see TRUE autonomous AI collaboration!** 🤖🤝🤖
