/**
 * Blueprint Routes
 * Team templates and cloning
 * Part of MD-598
 */

import { Router } from 'express';
import { prisma } from '../config/database';

export const blueprintRoutes = Router();

// GET /api/teams/blueprints - List blueprints
blueprintRoutes.get('/', async (req, res, next) => {
  try {
    const { teamType, domain, visibility } = req.query;

    const where: any = {};
    if (teamType) where.teamType = teamType;
    if (domain) where.domain = domain;
    if (visibility) where.visibility = visibility;

    const blueprints = await prisma.teamBlueprint.findMany({
      where,
      orderBy: { createdAt: 'desc' }
    });

    res.json({ blueprints });
  } catch (error) {
    next(error);
  }
});

// GET /api/teams/blueprints/:id - Get blueprint details
blueprintRoutes.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    const blueprint = await prisma.teamBlueprint.findUnique({
      where: { id },
      include: {
        sourceTeam: {
          select: {
            id: true,
            name: true,
            displayName: true,
            avgSynergyScore: true
          }
        }
      }
    });

    if (!blueprint) {
      return res.status(404).json({ error: 'Blueprint not found' });
    }

    res.json({ blueprint });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/teams/blueprints/:id - Delete blueprint
blueprintRoutes.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    await prisma.teamBlueprint.delete({
      where: { id }
    });

    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});
