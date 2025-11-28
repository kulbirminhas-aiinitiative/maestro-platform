/**
 * Team Routes
 * CRUD and member management for hybrid teams
 * Part of MD-598
 */

import { Router } from 'express';
import { prisma } from '../config/database';
import { v4 as uuidv4 } from 'uuid';

export const teamRoutes = Router();

// GET /api/teams - List all teams
teamRoutes.get('/', async (req, res, next) => {
  try {
    const { status, teamType } = req.query;

    const where: any = {};
    if (status) where.status = status;
    if (teamType) where.teamType = teamType;

    const teams = await prisma.hybridTeam.findMany({
      where,
      include: {
        members: {
          where: { status: 'active' },
          select: {
            id: true,
            memberId: true,
            memberType: true,
            memberName: true,
            teamRole: true,
          }
        },
        _count: {
          select: { members: true, interactions: true }
        }
      },
      orderBy: { updatedAt: 'desc' }
    });

    res.json({ teams });
  } catch (error) {
    next(error);
  }
});

// GET /api/teams/:id - Get team details
teamRoutes.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    const team = await prisma.hybridTeam.findUnique({
      where: { id },
      include: {
        members: {
          where: { status: 'active' },
          orderBy: { joinedAt: 'asc' }
        },
        cortex: true
      }
    });

    if (!team) {
      return res.status(404).json({ error: 'Team not found' });
    }

    res.json({
      team,
      members: team.members,
      cortex: team.cortex
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/create - Create new team
teamRoutes.post('/create', async (req, res, next) => {
  try {
    const {
      name,
      displayName,
      teamType,
      objective,
      description,
      domain,
      tags,
      metadata,
      createdBy
    } = req.body;

    // Create team with cortex
    const team = await prisma.hybridTeam.create({
      data: {
        name: name || `team-${uuidv4().slice(0, 8)}`,
        displayName: displayName || name,
        teamType: teamType || 'augmentation',
        objective: objective || '',
        description,
        domain,
        tags: tags || [],
        metadata: metadata || {},
        createdBy,
        cortex: {
          create: {}
        }
      },
      include: {
        cortex: true
      }
    });

    res.status(201).json({ team });
  } catch (error) {
    next(error);
  }
});

// PUT /api/teams/:id - Update team
teamRoutes.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const updates = req.body;

    const team = await prisma.hybridTeam.update({
      where: { id },
      data: updates
    });

    res.json({ team });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/teams/:id - Archive team
teamRoutes.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    await prisma.hybridTeam.update({
      where: { id },
      data: { status: 'archived' }
    });

    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/:id/add-member - Add member to team
teamRoutes.post('/:id/add-member', async (req, res, next) => {
  try {
    const { id } = req.params;
    const {
      memberId,
      memberType,
      memberName,
      teamRole,
      roleDescription
    } = req.body;

    const member = await prisma.teamMember.create({
      data: {
        teamId: id,
        memberId,
        memberType: memberType || 'human',
        memberName,
        teamRole: teamRole || 'member',
        roleDescription
      }
    });

    res.status(201).json({ member });
  } catch (error) {
    next(error);
  }
});

// GET /api/teams/:id/members - Get team members
teamRoutes.get('/:id/members', async (req, res, next) => {
  try {
    const { id } = req.params;

    const members = await prisma.teamMember.findMany({
      where: { teamId: id, status: 'active' },
      orderBy: { joinedAt: 'asc' }
    });

    res.json({ members });
  } catch (error) {
    next(error);
  }
});

// PUT /api/teams/:id/members/:memberId/role - Update member role
teamRoutes.put('/:id/members/:memberId/role', async (req, res, next) => {
  try {
    const { id, memberId } = req.params;
    const { teamRole, roleDescription } = req.body;

    const member = await prisma.teamMember.update({
      where: {
        teamId_memberId: { teamId: id, memberId }
      },
      data: { teamRole, roleDescription }
    });

    res.json({ member });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/teams/:id/members/:memberId - Remove member
teamRoutes.delete('/:id/members/:memberId', async (req, res, next) => {
  try {
    const { id, memberId } = req.params;

    await prisma.teamMember.update({
      where: {
        teamId_memberId: { teamId: id, memberId }
      },
      data: {
        status: 'removed',
        leftAt: new Date()
      }
    });

    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/:id/interactions/log - Log interaction
teamRoutes.post('/:id/interactions/log', async (req, res, next) => {
  try {
    const { id } = req.params;
    const interactionData = req.body;

    const interaction = await prisma.teamInteraction.create({
      data: {
        teamId: id,
        ...interactionData
      }
    });

    // Update team metrics
    await prisma.hybridTeam.update({
      where: { id },
      data: {
        totalInteractions: { increment: 1 }
      }
    });

    res.status(201).json({ interaction });
  } catch (error) {
    next(error);
  }
});

// GET /api/teams/:id/interactions - Get interactions
teamRoutes.get('/:id/interactions', async (req, res, next) => {
  try {
    const { id } = req.params;
    const limit = parseInt(req.query.limit as string) || 100;

    const interactions = await prisma.teamInteraction.findMany({
      where: { teamId: id },
      orderBy: { createdAt: 'desc' },
      take: limit
    });

    res.json({ interactions });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/:id/learning/record - Record learning event
teamRoutes.post('/:id/learning/record', async (req, res, next) => {
  try {
    const { id } = req.params;
    const learningData = req.body;

    const learningEvent = await prisma.teamLearningEvent.create({
      data: {
        teamId: id,
        ...learningData
      }
    });

    res.status(201).json({ learningEvent });
  } catch (error) {
    next(error);
  }
});

// GET /api/teams/:id/learning - Get learning events
teamRoutes.get('/:id/learning', async (req, res, next) => {
  try {
    const { id } = req.params;
    const limit = parseInt(req.query.limit as string) || 100;

    const learningEvents = await prisma.teamLearningEvent.findMany({
      where: { teamId: id },
      orderBy: { createdAt: 'desc' },
      take: limit
    });

    res.json({ learningEvents });
  } catch (error) {
    next(error);
  }
});

// GET /api/teams/:id/cortex-state - Get cortex state
teamRoutes.get('/:id/cortex-state', async (req, res, next) => {
  try {
    const { id } = req.params;

    const cortex = await prisma.teamCortex.findUnique({
      where: { teamId: id }
    });

    res.json({ cortex });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/:id/cortex/analyze - Analyze team cortex
teamRoutes.post('/:id/cortex/analyze', async (req, res, next) => {
  try {
    const { id } = req.params;

    // Get team data for analysis
    const team = await prisma.hybridTeam.findUnique({
      where: { id },
      include: {
        members: { where: { status: 'active' } },
        interactions: { take: 100, orderBy: { createdAt: 'desc' } }
      }
    });

    if (!team) {
      return res.status(404).json({ error: 'Team not found' });
    }

    // Calculate synergy metrics (simplified)
    const totalInteractions = team.interactions.length;
    const avgQuality = team.interactions.reduce((sum, i) => sum + (i.outcomeQuality || 0), 0) / (totalInteractions || 1);
    const avgFriction = team.interactions.reduce((sum, i) => sum + (i.frictionScore || 0), 0) / (totalInteractions || 1);

    const synergyMetrics = {
      interactionFriction: avgFriction,
      mutualLearningRate: team.interactions.filter(i => i.learningSignal).length / (totalInteractions || 1),
      timeToInsightMs: null,
      collaborationEfficiency: avgQuality * (1 - avgFriction)
    };

    // Update cortex
    const cortex = await prisma.teamCortex.update({
      where: { teamId: id },
      data: {
        ...synergyMetrics,
        lastAnalysisAt: new Date()
      }
    });

    res.json({
      analysis: {
        synergyMetrics,
        cortex
      }
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/:id/stage/advance - Advance team stage
teamRoutes.post('/:id/stage/advance', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { transitionReason, triggeredBy } = req.body;

    const team = await prisma.hybridTeam.findUnique({
      where: { id }
    });

    if (!team) {
      return res.status(404).json({ error: 'Team not found' });
    }

    // Define stage progression
    const stageOrder = ['assembly', 'synchronization', 'stress_test', 'symbiosis', 'transcendence'];
    const currentIndex = stageOrder.indexOf(team.currentStage);

    if (currentIndex >= stageOrder.length - 1) {
      return res.status(400).json({ error: 'Team is already at highest stage' });
    }

    const nextStage = stageOrder[currentIndex + 1] as any;

    // Create transition record
    await prisma.stageTransition.create({
      data: {
        teamId: id,
        fromStage: team.currentStage,
        toStage: nextStage,
        transitionReason,
        triggeredBy: triggeredBy || 'manual',
        metricsSnapshot: {}
      }
    });

    // Update team
    const updatedTeam = await prisma.hybridTeam.update({
      where: { id },
      data: {
        currentStage: nextStage,
        stageStartedAt: new Date()
      }
    });

    res.json({ team: updatedTeam, previousStage: team.currentStage });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/:id/blueprint/extract - Extract blueprint from team
teamRoutes.post('/:id/blueprint/extract', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { name, displayName, description, visibility, tags } = req.body;

    const team = await prisma.hybridTeam.findUnique({
      where: { id },
      include: {
        members: { where: { status: 'active' } },
        cortex: true
      }
    });

    if (!team) {
      return res.status(404).json({ error: 'Team not found' });
    }

    // Extract required roles from members
    const requiredRoles = team.members.map(m => ({
      role: m.teamRole,
      memberType: m.memberType,
      roleDescription: m.roleDescription,
      avgQuality: m.avgContributionQuality
    }));

    const blueprint = await prisma.teamBlueprint.create({
      data: {
        sourceTeamId: id,
        name: name || `${team.name}-blueprint`,
        displayName: displayName || `${team.displayName} Blueprint`,
        description,
        teamType: team.teamType,
        domain: team.domain,
        avgSynergyScore: team.avgSynergyScore,
        totalSuccessfulOutcomes: team.successfulOutcomes,
        requiredRoles,
        optimalTeamSize: team.members.length,
        communicationProtocols: team.cortex?.communicationProtocols || {},
        workflowPatterns: team.cortex?.currentWorkflow || {},
        learnedOptimizations: team.cortex?.learnedPatterns || {},
        tags: tags || team.tags,
        visibility: visibility || 'private'
      }
    });

    res.status(201).json({ blueprintId: blueprint.id, blueprint });
  } catch (error) {
    next(error);
  }
});

// POST /api/teams/from-blueprint - Create team from blueprint
teamRoutes.post('/from-blueprint', async (req, res, next) => {
  try {
    const { blueprintId, name, displayName, objective, createdBy } = req.body;

    const blueprint = await prisma.teamBlueprint.findUnique({
      where: { id: blueprintId }
    });

    if (!blueprint) {
      return res.status(404).json({ error: 'Blueprint not found' });
    }

    // Create team from blueprint
    const team = await prisma.hybridTeam.create({
      data: {
        name: name || `${blueprint.name}-clone-${uuidv4().slice(0, 8)}`,
        displayName: displayName || blueprint.displayName,
        teamType: blueprint.teamType,
        objective: objective || '',
        domain: blueprint.domain,
        tags: blueprint.tags,
        createdBy,
        cortex: {
          create: {
            communicationProtocols: blueprint.communicationProtocols as any,
            currentWorkflow: blueprint.workflowPatterns as any,
            learnedPatterns: blueprint.learnedOptimizations as any
          }
        }
      }
    });

    // Increment clone count
    await prisma.teamBlueprint.update({
      where: { id: blueprintId },
      data: { timesCloned: { increment: 1 } }
    });

    res.status(201).json({ teamId: team.id, team });
  } catch (error) {
    next(error);
  }
});
