# Domain-Specific Team Examples

Real-world multi-agent collaboration examples across different domains and team sizes.

## Examples Overview

| Example | Domain | Team Size | Key Roles | Scenario |
|---------|--------|-----------|-----------|----------|
| **Medical Team** | Healthcare | 5 | Doctor, Specialists, Nurse, Pharmacist | Patient diagnosis & treatment |
| **Educational Team** | Education | 7 | Teachers, Students, TA, Counselor | Collaborative learning project |
| **Research Team** | Science | 4 | PI, Scientist, Analyst, Writer | Drug research collaboration |
| **Business Team** | Corporate | 8 | PM, Designers, Marketing, Sales, Ops | Product launch planning |
| **Emergency Response** | Public Safety | 6 | Incident Cmd, Fire, Police, EMS, Comms | Crisis coordination |
| **Team Size Comparison** | Analysis | 2, 5, 10 | Various | Communication complexity analysis |

---

## 1. Medical Team (5 members)

**File:** `medical_team.py`

### Team Composition
- Dr. Williams (Lead Physician)
- Dr. Patel (Cardiologist)
- Dr. Chen (Neurologist)
- Nurse Garcia (RN)
- Pharm. Johnson (Clinical Pharmacist)

### Scenario
68-year-old patient with chest pain, dizziness, and confusion. Team collaborates to diagnose atrial fibrillation with possible stroke.

### Communication Highlights
- Specialist consultations via targeted messages
- Knowledge sharing (patient vitals, findings)
- Collaborative decision making with voting
- Medication safety review
- Integrated care coordination

### Run Example
```bash
python examples/domain_teams/medical_team.py
```

### Key Takeaways
- Specialists provide domain expertise
- Pharmacist ensures medication safety
- Lead physician integrates findings
- Team consensus through voting
- Patient safety prioritized throughout

---

## 2. Educational Team (7 members)

**File:** `educational_team.py`

### Team Composition
- Ms. Rodriguez (Lead Teacher - Science)
- Mr. Kim (Math Teacher)
- Emma (Student - Research & Writing)
- Raj (Student - Data Analysis)
- Sofia (Student - Visual Design)
- TA James (Teaching Assistant)
- Counselor Lee (Academic Counselor)

### Scenario
Group project on climate change with collaborative research, data analysis, and presentation.

### Communication Highlights
- Students claim tasks based on strengths
- Peer-to-peer knowledge sharing
- Teacher guidance and scaffolding
- TA support for struggling students
- Counselor promotes collaboration

### Run Example
```bash
python examples/domain_teams/educational_team.py
```

### Key Takeaways
- Students learn through collaboration
- Peer teaching enhances understanding
- Adults provide scaffolding, not answers
- Different strengths complement each other
- Growth mindset fostered throughout

---

## 3. Research Team (4 members)

**File:** `research_team.py`

### Team Composition
- Dr. Martinez (Principal Investigator)
- Dr. Chen (Research Scientist)
- Dr. Patel (Data Analyst)
- Dr. Kim (Research Writer)

### Scenario
Testing new antibiotic compound XR-47 for efficacy against multi-drug resistant bacteria.

### Communication Highlights
- PI sets research hypothesis
- Scientist shares experimental data
- Analyst provides statistical analysis
- Writer prepares manuscript
- Collaborative publication strategy

### Run Example
```bash
python examples/domain_teams/research_team.py
```

### Key Takeaways
- Small focused teams for specialized work
- Clear role division (lab/analysis/writing)
- Evidence-based collaboration
- Statistical rigor emphasized
- Publication as team goal

---

## 4. Business Team (8 members)

**File:** `business_team.py`

### Team Composition
- Sarah (Product Manager)
- David (Business Analyst)
- Alex & Maya (UX/UI Designers)
- James & Priya (Brand/Digital Marketing)
- Lisa (Sales Lead)
- Mike (Operations Manager)

### Scenario
Launching CloudSync Pro SaaS product in competitive market with 30-day timeline.

### Communication Highlights
- Cross-functional coordination
- Sub-team formation (Design, Marketing, Sales)
- Parallel workstreams
- Market research integration
- Launch readiness alignment

### Run Example
```bash
python examples/domain_teams/business_team.py
```

### Key Takeaways
- Cross-functional teams require coordination
- Sub-teams form around specializations
- Parallel work accelerates timeline
- Regular alignment critical
- Clear goals unite diverse roles

---

## 5. Emergency Response Team (6 members)

**File:** `emergency_response_team.py`

### Team Composition
- Commander Rodriguez (Incident Commander)
- Chief Martinez (Fire Operations)
- Medic Chen (EMS Coordinator)
- Sgt. Williams (Police Coordinator)
- PIO Jackson (Communications Officer)
- Log. Patel (Logistics Coordinator)

### Scenario
Multi-vehicle accident with hazmat spill requiring rapid coordinated response.

### Communication Highlights
- Unified command structure
- Real-time situation updates
- Priority-based decision making
- Inter-agency coordination
- Public information management

### Run Example
```bash
python examples/domain_teams/emergency_response_team.py
```

### Key Takeaways
- Time-critical coordination
- Clear command structure essential
- Real-time information sharing
- Priority-based resource allocation
- Multiple agencies work as one team

---

## 6. Team Size Comparison (2, 5, 10 members)

**File:** `team_size_comparison.py`

### Scenarios
- **Small (2):** Doctor + Nurse consultation
- **Medium (5):** Software development team
- **Large (10):** Enterprise project team

### Communication Analysis
Demonstrates how communication complexity changes with team size:
- Small teams: Direct 1:1 communication
- Medium teams: Mix of broadcast + targeted messaging
- Large teams: Multiple parallel threads + sub-teams

### Run Example
```bash
python examples/domain_teams/team_size_comparison.py
```

### Key Insights
- Communication complexity grows exponentially
- Teams > 7-8 benefit from sub-team structure
- Shared MCP scales seamlessly
- Knowledge sharing critical in larger teams
- Clear roles essential for all sizes

---

## Running All Examples

### Run Individual Example
```bash
# Medical team
python examples/domain_teams/medical_team.py

# Educational team
python examples/domain_teams/educational_team.py

# Research team
python examples/domain_teams/research_team.py

# Business team
python examples/domain_teams/business_team.py

# Emergency response
python examples/domain_teams/emergency_response_team.py

# Team size comparison
python examples/domain_teams/team_size_comparison.py
```

### Run All Examples
```bash
# From the examples directory
for file in domain_teams/*.py; do
    echo "Running $file"
    python "$file"
    echo "---"
done
```

---

## Communication Patterns Observed

### 1. Direct Messaging (1:1)
```python
await agent_a.send_message("agent_b", "Need your input on X", "request")
await agent_b.send_message("agent_a", "Here's my analysis...", "response")
```
**Used in:** All teams, especially for specialized consultations

### 2. Broadcast Messaging (1:All)
```python
await leader.send_message("all", "Team update: ...", "broadcast")
```
**Used in:** Announcements, status updates, team-wide alerts

### 3. Knowledge Sharing
```python
await agent_a.share_knowledge("key", "value", "category")
value = await agent_b.get_knowledge("key")
```
**Used in:** Sharing findings, data, guidelines, best practices

### 4. Collaborative Decision Making
```python
await agent.propose_decision("decision", "rationale")
await other_agent.vote_decision("decision_id", "approve")
```
**Used in:** Medical diagnoses, project approvals, strategic choices

### 5. Sub-team Coordination
```python
# Frontend sub-team communicates separately
await frontend_1.send_message("frontend_2", "Let's align on design")
await frontend_2.send_message("frontend_1", "Agreed, I'll lead component lib")
```
**Used in:** Large teams (8+) with specialized sub-groups

---

## Key Learnings by Domain

### Healthcare
- Evidence-based decision making
- Patient safety paramount
- Specialist expertise valued
- Interdisciplinary collaboration
- Documentation critical

### Education
- Peer learning powerful
- Scaffolding over direct answers
- Strength-based task assignment
- Growth mindset fostered
- Multiple support layers

### Research
- Hypothesis-driven work
- Statistical rigor essential
- Clear role specialization
- Publication as shared goal
- Peer review integrated

### Business
- Cross-functional alignment critical
- Parallel workstreams accelerate delivery
- Market data informs strategy
- Sub-team autonomy with coordination
- Clear metrics and goals

### Emergency Response
- Time-critical coordination
- Unified command structure
- Real-time information sharing
- Multi-agency cooperation
- Public communication managed

---

## Customization Guide

### Adapt for Your Domain

1. **Define Roles**
   ```python
   class CustomAgent(TeamAgent):
       def __init__(self, agent_id, specialty, coord_server):
           self.specialty = specialty
           config = AgentConfig(
               agent_id=agent_id,
               role=AgentRole.DEVELOPER,
               system_prompt=f"You are {agent_id}, a {specialty}..."
           )
           super().__init__(config, coord_server)
   ```

2. **Set Communication Patterns**
   - Identify who needs to talk to whom
   - Decide on broadcast vs targeted messages
   - Define knowledge sharing categories

3. **Create Workflows**
   - Map out collaboration steps
   - Identify decision points
   - Plan knowledge hand-offs

4. **Add Domain Knowledge**
   - Share industry-specific information
   - Use domain terminology
   - Include best practices

---

## Performance Notes

### Message Volume by Team Size
- Small (2-3): 5-15 messages
- Medium (4-7): 15-40 messages
- Large (8-10): 40-100+ messages

### Optimal Team Sizes
- **2-3:** Simple tasks, quick decisions
- **4-7:** Most projects, balanced complexity
- **8-10:** Large projects, requires sub-teams
- **10+:** Complex initiatives, formal structure needed

---

## Future Examples

Potential additional domains:
- Legal team (attorneys, paralegals, researchers)
- Creative agency (designers, copywriters, strategists)
- Construction project (architect, engineers, contractors)
- Restaurant operations (chef, sous chef, servers, manager)
- Event planning (coordinator, vendors, logistics)

---

## Support

For questions or suggestions about these examples:
- Review main SDK documentation: `../README.md`
- Check quickstart guide: `../QUICKSTART.md`
- See architecture docs: `../ARCHITECTURE.md`

