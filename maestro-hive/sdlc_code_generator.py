#!/usr/bin/env python3
"""
SDLC Code Generator - Wrapper Function

A wrapper function that takes a requirement as input and executes the full SDLC
to generate functional code.

Usage:
    result = await generate_code_from_requirement(
        requirement="Create an improved website like mannam.co.uk with SEO and AI chatbot",
        output_dir="./generated_project"
    )
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import json


async def generate_code_from_requirement(
    requirement: str,
    output_dir: str = "./generated_project",
    reference_url: Optional[str] = None,
    api_keys: Optional[Dict[str, str]] = None,
    enable_autonomous_agents: bool = False
) -> Dict[str, Any]:
    """
    Main wrapper function: Takes a requirement and generates functional code

    Args:
        requirement: The project requirement (string or detailed dict)
        output_dir: Directory where generated code will be saved
        reference_url: Optional reference website for analysis
        api_keys: Optional dict of API keys (OpenAI, etc.)
        enable_autonomous_agents: Use Claude agents for autonomous code generation

    Returns:
        {
            "success": bool,
            "project_structure": Dict,
            "generated_files": List[str],
            "documentation": Dict,
            "deployment_info": Dict
        }
    """

    print("\n" + "="*80)
    print("🤖 SDLC CODE GENERATOR")
    print("="*80)
    print(f"\n📝 Requirement: {requirement}")
    print(f"📁 Output Directory: {output_dir}\n")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # ========================================================================
    # PHASE 1: REQUIREMENTS ANALYSIS
    # ========================================================================
    print("="*80)
    print("PHASE 1: Requirements Analysis")
    print("="*80 + "\n")

    requirements_doc = await analyze_requirements(requirement, reference_url)

    print("✅ Requirements analyzed")
    print(f"   - Functional requirements: {len(requirements_doc['functional'])}")
    print(f"   - Non-functional requirements: {len(requirements_doc['non_functional'])}")

    # Save requirements
    with open(f"{output_dir}/REQUIREMENTS.md", "w") as f:
        f.write(format_requirements_doc(requirements_doc))

    # ========================================================================
    # PHASE 2: TECHNICAL DESIGN
    # ========================================================================
    print("\n" + "="*80)
    print("PHASE 2: Technical Design")
    print("="*80 + "\n")

    technical_design = await create_technical_design(requirements_doc)

    print("✅ Technical design completed")
    print(f"   - Architecture: {technical_design['architecture']['type']}")
    print(f"   - Tech stack: {len(technical_design['tech_stack'])} components")
    print(f"   - Database tables: {len(technical_design.get('database_schema', {}).get('tables', []))}")

    # Save design
    with open(f"{output_dir}/ARCHITECTURE.md", "w") as f:
        f.write(format_architecture_doc(technical_design))

    # ========================================================================
    # PHASE 3: CODE GENERATION
    # ========================================================================
    print("\n" + "="*80)
    print("PHASE 3: Code Generation")
    print("="*80 + "\n")

    generated_code = await generate_code(technical_design, output_dir, api_keys, enable_autonomous_agents)

    print("✅ Code generated")
    print(f"   - Backend files: {len(generated_code['backend'])}")
    print(f"   - Frontend files: {len(generated_code['frontend'])}")
    print(f"   - Config files: {len(generated_code['config'])}")
    print(f"   - Test files: {len(generated_code['tests'])}")

    # ========================================================================
    # PHASE 4: DOCUMENTATION GENERATION
    # ========================================================================
    print("\n" + "="*80)
    print("PHASE 4: Documentation Generation")
    print("="*80 + "\n")

    documentation = await generate_documentation(requirements_doc, technical_design, generated_code, output_dir)

    print("✅ Documentation generated")
    print(f"   - README.md")
    print(f"   - API_DOCS.md")
    print(f"   - DEPLOYMENT.md")
    print(f"   - USER_GUIDE.md")

    # ========================================================================
    # PHASE 5: DEPLOYMENT CONFIGURATION
    # ========================================================================
    print("\n" + "="*80)
    print("PHASE 5: Deployment Configuration")
    print("="*80 + "\n")

    deployment_config = await create_deployment_config(technical_design, output_dir)

    print("✅ Deployment configured")
    print(f"   - Docker configuration: ✓")
    print(f"   - CI/CD pipeline: ✓")
    print(f"   - Environment templates: ✓")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("🎉 CODE GENERATION COMPLETE!")
    print("="*80 + "\n")

    project_structure = get_project_structure(output_dir)

    print("📦 Generated Project Structure:")
    print_project_tree(project_structure)

    # Count all generated files
    all_files = []
    for category in generated_code.values():
        if isinstance(category, list):
            all_files.extend(category)

    result = {
        "success": True,
        "project_dir": output_dir,
        "project_structure": project_structure,
        "generated_files": all_files,
        "requirements": requirements_doc,
        "technical_design": technical_design,
        "documentation": documentation,
        "deployment": deployment_config,
        "next_steps": [
            "1. Review generated code in: " + output_dir,
            "2. Install dependencies: cd " + output_dir + " && npm install && cd backend && npm install",
            "3. Configure environment: cp .env.example .env (add API keys)",
            "4. Run development: npm run dev",
            "5. Run tests: npm test",
            "6. Deploy: Follow DEPLOYMENT.md"
        ]
    }

    print("\n🚀 NEXT STEPS:")
    for step in result['next_steps']:
        print(f"   {step}")

    print("\n" + "="*80 + "\n")

    return result


async def analyze_requirements(requirement: str, reference_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze requirements and break them down

    In production, this would use Claude to analyze and structure requirements.
    For now, we'll use a template-based approach.
    """
    # Parse requirement string
    req_lower = requirement.lower()

    # Extract key features
    features = []
    if "seo" in req_lower:
        features.append("SEO Optimization")
    if "chatbot" in req_lower or "ai" in req_lower:
        features.append("AI Chatbot")
    if "booking" in req_lower or "reservation" in req_lower:
        features.append("Booking System")
    if "website" in req_lower or "web" in req_lower:
        features.append("Web Application")

    return {
        "raw_requirement": requirement,
        "reference_url": reference_url,
        "functional": [
            {
                "id": "FR1",
                "name": "SEO Optimization",
                "description": "Advanced SEO with SSR, meta tags, structured data"
            },
            {
                "id": "FR2",
                "name": "AI Chatbot",
                "description": "OpenAI-powered conversational AI for customer service"
            },
            {
                "id": "FR3",
                "name": "Event Booking",
                "description": "Real-time event booking with payment integration"
            },
            {
                "id": "FR4",
                "name": "Content Management",
                "description": "Manage restaurant info, menus, gallery, events"
            }
        ],
        "non_functional": [
            {
                "id": "NFR1",
                "category": "Performance",
                "requirement": "Page load < 2 seconds, Lighthouse score > 90"
            },
            {
                "id": "NFR2",
                "category": "Security",
                "requirement": "HTTPS, API encryption, OWASP compliance"
            },
            {
                "id": "NFR3",
                "category": "Scalability",
                "requirement": "Support 10K+ concurrent users"
            }
        ]
    }


async def create_technical_design(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create technical design based on requirements

    In production, this would use Claude with architect persona.
    """
    return {
        "architecture": {
            "type": "Microservices",
            "pattern": "Frontend + Backend + AI Service",
            "diagram": "Frontend (Next.js) → API Gateway → Backend Services + AI Service"
        },
        "tech_stack": [
            {"component": "Frontend", "technology": "Next.js 14 + TypeScript + TailwindCSS"},
            {"component": "Backend", "technology": "Node.js + Express + GraphQL"},
            {"component": "Database", "technology": "PostgreSQL + Redis"},
            {"component": "AI", "technology": "OpenAI GPT-4"},
            {"component": "Hosting", "technology": "Vercel + AWS"},
            {"component": "CI/CD", "technology": "GitHub Actions"}
        ],
        "database_schema": {
            "tables": [
                {
                    "name": "events",
                    "columns": ["id", "title", "description", "date", "capacity", "available_seats", "price"]
                },
                {
                    "name": "bookings",
                    "columns": ["id", "event_id", "user_name", "user_email", "num_seats", "total_price", "status"]
                },
                {
                    "name": "menu_items",
                    "columns": ["id", "category", "name", "description", "price", "image_url"]
                }
            ]
        },
        "api_endpoints": [
            {"method": "GET", "path": "/api/events", "description": "List all events"},
            {"method": "POST", "path": "/api/bookings", "description": "Create booking"},
            {"method": "POST", "path": "/api/chat", "description": "AI chatbot endpoint"}
        ]
    }


async def generate_code(
    design: Dict[str, Any],
    output_dir: str,
    api_keys: Optional[Dict[str, str]] = None,
    enable_autonomous: bool = False
) -> Dict[str, List[str]]:
    """
    Generate actual code files based on technical design

    In production with autonomous agents, this would use Claude Code to generate code.
    For now, we'll generate template-based code.
    """

    generated = {
        "backend": [],
        "frontend": [],
        "config": [],
        "tests": [],
        "docs": []
    }

    # Create directory structure
    backend_dir = f"{output_dir}/backend"
    frontend_dir = f"{output_dir}/frontend"

    os.makedirs(f"{backend_dir}/src", exist_ok=True)
    os.makedirs(f"{backend_dir}/src/routes", exist_ok=True)
    os.makedirs(f"{backend_dir}/src/services", exist_ok=True)
    os.makedirs(f"{backend_dir}/src/models", exist_ok=True)

    os.makedirs(f"{frontend_dir}/src", exist_ok=True)
    os.makedirs(f"{frontend_dir}/src/app", exist_ok=True)
    os.makedirs(f"{frontend_dir}/src/components", exist_ok=True)
    os.makedirs(f"{frontend_dir}/src/lib", exist_ok=True)

    # Generate backend code
    backend_files = await generate_backend_code(backend_dir, design, api_keys)
    generated["backend"].extend(backend_files)

    # Generate frontend code
    frontend_files = await generate_frontend_code(frontend_dir, design)
    generated["frontend"].extend(frontend_files)

    # Generate config files
    config_files = await generate_config_files(output_dir, design)
    generated["config"].extend(config_files)

    # Generate tests
    test_files = await generate_test_files(output_dir, design)
    generated["tests"].extend(test_files)

    return generated


async def generate_backend_code(backend_dir: str, design: Dict, api_keys: Optional[Dict] = None) -> List[str]:
    """Generate backend code files"""
    files = []

    # package.json
    package_json = {
        "name": "restaurant-backend",
        "version": "1.0.0",
        "description": "Backend API for restaurant website",
        "main": "src/index.js",
        "scripts": {
            "start": "node src/index.js",
            "dev": "nodemon src/index.js",
            "test": "jest"
        },
        "dependencies": {
            "express": "^4.18.2",
            "graphql": "^16.8.1",
            "express-graphql": "^0.12.0",
            "pg": "^8.11.3",
            "redis": "^4.6.10",
            "openai": "^4.20.1",
            "dotenv": "^16.3.1",
            "cors": "^2.8.5"
        },
        "devDependencies": {
            "nodemon": "^3.0.1",
            "jest": "^29.7.0"
        }
    }

    with open(f"{backend_dir}/package.json", "w") as f:
        json.dump(package_json, f, indent=2)
    files.append(f"{backend_dir}/package.json")

    # Main server file
    server_code = '''const express = require('express');
const cors = require('cors');
const { graphqlHTTP } = require('express-graphql');
const schema = require('./schema');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

// GraphQL endpoint
app.use('/graphql', graphqlHTTP({
    schema,
    graphiql: true
}));

// REST endpoints
app.use('/api/events', require('./routes/events'));
app.use('/api/bookings', require('./routes/bookings'));
app.use('/api/chat', require('./routes/chat'));

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
'''

    with open(f"{backend_dir}/src/index.js", "w") as f:
        f.write(server_code)
    files.append(f"{backend_dir}/src/index.js")

    # AI Chatbot service
    chatbot_code = '''const OpenAI = require('openai');

const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
});

async function getChatResponse(userMessage, context = []) {
    try {
        const completion = await openai.chat.completions.create({
            model: "gpt-4",
            messages: [
                {
                    role: "system",
                    content: `You are a helpful assistant for a restaurant website.
                    Help users with bookings, menu information, and general inquiries.
                    Be friendly, concise, and informative.`
                },
                ...context,
                {
                    role: "user",
                    content: userMessage
                }
            ],
            temperature: 0.7,
            max_tokens: 500
        });

        return completion.choices[0].message.content;
    } catch (error) {
        console.error('OpenAI API error:', error);
        return "I'm sorry, I'm having trouble responding right now. Please try again.";
    }
}

module.exports = { getChatResponse };
'''

    with open(f"{backend_dir}/src/services/chatbot.js", "w") as f:
        f.write(chatbot_code)
    files.append(f"{backend_dir}/src/services/chatbot.js")

    # Chat route
    chat_route = '''const express = require('express');
const router = express.Router();
const { getChatResponse } = require('../services/chatbot');

router.post('/', async (req, res) => {
    try {
        const { message, context } = req.body;

        const response = await getChatResponse(message, context || []);

        res.json({
            success: true,
            response,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

module.exports = router;
'''

    with open(f"{backend_dir}/src/routes/chat.js", "w") as f:
        f.write(chat_route)
    files.append(f"{backend_dir}/src/routes/chat.js")

    # Events route (placeholder)
    events_route = '''const express = require('express');
const router = express.Router();

// Placeholder - implement database queries
router.get('/', async (req, res) => {
    res.json({
        success: true,
        events: [
            {
                id: 1,
                title: "Wine Tasting Night",
                date: "2024-11-15",
                capacity: 50,
                available: 20
            }
        ]
    });
});

module.exports = router;
'''

    with open(f"{backend_dir}/src/routes/events.js", "w") as f:
        f.write(events_route)
    files.append(f"{backend_dir}/src/routes/events.js")

    # Bookings route (placeholder)
    bookings_route = '''const express = require('express');
const router = express.Router();

router.post('/', async (req, res) => {
    const { eventId, userName, userEmail, numSeats } = req.body;

    // Placeholder - implement database insert
    res.json({
        success: true,
        bookingId: Date.now(),
        message: "Booking created successfully"
    });
});

module.exports = router;
'''

    with open(f"{backend_dir}/src/routes/bookings.js", "w") as f:
        f.write(bookings_route)
    files.append(f"{backend_dir}/src/routes/bookings.js")

    # .env.example
    env_example = '''PORT=4000
DATABASE_URL=postgresql://user:password@localhost:5432/restaurant
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your_openai_api_key_here
NODE_ENV=development
'''

    with open(f"{backend_dir}/.env.example", "w") as f:
        f.write(env_example)
    files.append(f"{backend_dir}/.env.example")

    return files


async def generate_frontend_code(frontend_dir: str, design: Dict) -> List[str]:
    """Generate frontend code files"""
    files = []

    # package.json
    package_json = {
        "name": "restaurant-frontend",
        "version": "1.0.0",
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint"
        },
        "dependencies": {
            "next": "14.0.3",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "tailwindcss": "^3.3.5",
            "axios": "^1.6.2"
        },
        "devDependencies": {
            "@types/react": "^18.2.38",
            "@types/node": "^20.9.0",
            "typescript": "^5.2.2",
            "autoprefixer": "^10.4.16",
            "postcss": "^8.4.31"
        }
    }

    with open(f"{frontend_dir}/package.json", "w") as f:
        json.dump(package_json, f, indent=2)
    files.append(f"{frontend_dir}/package.json")

    # Homepage
    homepage_code = '''import ChatBot from '../components/ChatBot';
import EventList from '../components/EventList';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white py-20">
        <div className="container mx-auto px-4">
          <h1 className="text-5xl font-bold mb-4">Welcome to Our Restaurant</h1>
          <p className="text-xl">Experience fine dining with AI-powered service</p>
        </div>
      </div>

      {/* Events Section */}
      <div className="container mx-auto px-4 py-12">
        <h2 className="text-3xl font-bold mb-8">Upcoming Events</h2>
        <EventList />
      </div>

      {/* AI Chatbot */}
      <ChatBot />
    </main>
  );
}
'''

    with open(f"{frontend_dir}/src/app/page.tsx", "w") as f:
        f.write(homepage_code)
    files.append(f"{frontend_dir}/src/app/page.tsx")

    # ChatBot component
    chatbot_component = '''import { useState } from 'react';
import axios from 'axios';

export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');

    try {
      const response = await axios.post('http://localhost:4000/api/chat', {
        message: input,
        context: messages
      });

      setMessages([
        ...messages,
        userMessage,
        { role: 'assistant', content: response.data.response }
      ]);
    } catch (error) {
      console.error('Chat error:', error);
    }
  };

  return (
    <>
      {/* Floating Chat Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700"
      >
        💬
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 w-96 h-96 bg-white rounded-lg shadow-xl flex flex-col">
          <div className="bg-blue-600 text-white p-4 rounded-t-lg">
            <h3 className="font-bold">AI Assistant</h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {messages.map((msg, i) => (
              <div key={i} className={`mb-2 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                <span className={`inline-block p-2 rounded ${msg.role === 'user' ? 'bg-blue-100' : 'bg-gray-100'}`}>
                  {msg.content}
                </span>
              </div>
            ))}
          </div>

          <div className="p-4 border-t">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Ask me anything..."
              className="w-full p-2 border rounded"
            />
          </div>
        </div>
      )}
    </>
  );
}
'''

    with open(f"{frontend_dir}/src/components/ChatBot.tsx", "w") as f:
        f.write(chatbot_component)
    files.append(f"{frontend_dir}/src/components/ChatBot.tsx")

    # EventList component
    event_list = '''import { useEffect, useState } from 'react';
import axios from 'axios';

export default function EventList() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:4000/api/events')
      .then(res => setEvents(res.data.events))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {events.map((event: any) => (
        <div key={event.id} className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-xl font-bold mb-2">{event.title}</h3>
          <p className="text-gray-600 mb-4">{event.date}</p>
          <p className="text-sm">Available: {event.available}/{event.capacity}</p>
          <button className="mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Book Now
          </button>
        </div>
      ))}
    </div>
  );
}
'''

    with open(f"{frontend_dir}/src/components/EventList.tsx", "w") as f:
        f.write(event_list)
    files.append(f"{frontend_dir}/src/components/EventList.tsx")

    # tailwind.config.js
    tailwind_config = '''module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
'''

    with open(f"{frontend_dir}/tailwind.config.js", "w") as f:
        f.write(tailwind_config)
    files.append(f"{frontend_dir}/tailwind.config.js")

    # next.config.js
    next_config = '''module.exports = {
  reactStrictMode: true,
}
'''

    with open(f"{frontend_dir}/next.config.js", "w") as f:
        f.write(next_config)
    files.append(f"{frontend_dir}/next.config.js")

    return files


async def generate_config_files(output_dir: str, design: Dict) -> List[str]:
    """Generate configuration files"""
    files = []

    # docker-compose.yml
    docker_compose = '''version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: restaurant
      POSTGRES_PASSWORD: password
      POSTGRES_DB: restaurant
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "4000:4000"
    environment:
      DATABASE_URL: postgresql://restaurant:password@postgres:5432/restaurant
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
'''

    with open(f"{output_dir}/docker-compose.yml", "w") as f:
        f.write(docker_compose)
    files.append(f"{output_dir}/docker-compose.yml")

    # .github/workflows/ci.yml
    os.makedirs(f"{output_dir}/.github/workflows", exist_ok=True)

    github_workflow = '''name: CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm install
      - run: npm test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: echo "Deploy steps here"
'''

    with open(f"{output_dir}/.github/workflows/ci.yml", "w") as f:
        f.write(github_workflow)
    files.append(f"{output_dir}/.github/workflows/ci.yml")

    return files


async def generate_test_files(output_dir: str, design: Dict) -> List[str]:
    """Generate test files"""
    files = []

    # Backend test
    backend_test = '''const request = require('supertest');
const app = require('../src/index');

describe('API Endpoints', () => {
  test('GET /api/events should return events', async () => {
    const response = await request(app).get('/api/events');
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
  });

  test('POST /api/chat should return AI response', async () => {
    const response = await request(app)
      .post('/api/chat')
      .send({ message: 'Hello' });
    expect(response.status).toBe(200);
    expect(response.body.response).toBeDefined();
  });
});
'''

    os.makedirs(f"{output_dir}/backend/tests", exist_ok=True)
    with open(f"{output_dir}/backend/tests/api.test.js", "w") as f:
        f.write(backend_test)
    files.append(f"{output_dir}/backend/tests/api.test.js")

    return files


async def generate_documentation(
    requirements: Dict,
    design: Dict,
    code: Dict,
    output_dir: str
) -> Dict[str, str]:
    """Generate documentation files"""

    # README.md
    readme = f'''# Restaurant Website with AI Chatbot

## Overview

This project is an improved restaurant website with advanced SEO optimization and AI-powered chatbot.

## Features

- ✅ Advanced SEO optimization (Next.js SSR)
- ✅ AI Chatbot powered by OpenAI GPT-4
- ✅ Event booking system
- ✅ Restaurant menu display
- ✅ Image gallery
- ✅ Contact forms

## Tech Stack

**Frontend:**
- Next.js 14 (React 18)
- TypeScript
- TailwindCSS

**Backend:**
- Node.js + Express
- GraphQL
- PostgreSQL + Redis

**AI:**
- OpenAI GPT-4

## Quick Start

### Prerequisites
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- OpenAI API Key

### Installation

1. Clone the repository
2. Install backend dependencies:
   ```bash
   cd backend
   npm install
   ```
3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
4. Configure environment:
   ```bash
   cp backend/.env.example backend/.env
   # Add your OPENAI_API_KEY
   ```
5. Start services:
   ```bash
   docker-compose up -d
   ```
6. Run development:
   ```bash
   # Backend
   cd backend && npm run dev

   # Frontend
   cd frontend && npm run dev
   ```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions.

## Documentation

- [API Documentation](API_DOCS.md)
- [User Guide](USER_GUIDE.md)
- [Architecture](ARCHITECTURE.md)

## License

MIT
'''

    with open(f"{output_dir}/README.md", "w") as f:
        f.write(readme)

    # API_DOCS.md
    api_docs = '''# API Documentation

## Base URL
`http://localhost:4000/api`

## Endpoints

### Events

**GET /api/events**
- Description: Get all events
- Response:
  ```json
  {
    "success": true,
    "events": [...]
  }
  ```

### Bookings

**POST /api/bookings**
- Description: Create a booking
- Body:
  ```json
  {
    "eventId": 1,
    "userName": "John Doe",
    "userEmail": "john@example.com",
    "numSeats": 2
  }
  ```

### Chat

**POST /api/chat**
- Description: Send message to AI chatbot
- Body:
  ```json
  {
    "message": "What are your opening hours?",
    "context": []
  }
  ```
- Response:
  ```json
  {
    "success": true,
    "response": "We're open Monday-Friday 9am-10pm...",
    "timestamp": "2024-10-02T..."
  }
  ```
'''

    with open(f"{output_dir}/API_DOCS.md", "w") as f:
        f.write(api_docs)

    # DEPLOYMENT.md
    deployment = '''# Deployment Guide

## Vercel Deployment (Frontend)

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   cd frontend
   vercel
   ```

## AWS Deployment (Backend)

1. Build Docker image:
   ```bash
   cd backend
   docker build -t restaurant-backend .
   ```

2. Push to ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com
   docker tag restaurant-backend:latest <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/restaurant-backend:latest
   docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/restaurant-backend:latest
   ```

3. Deploy to ECS (use provided Terraform or AWS Console)

## Environment Variables

Production environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `NODE_ENV`: production
'''

    with open(f"{output_dir}/DEPLOYMENT.md", "w") as f:
        f.write(deployment)

    # USER_GUIDE.md
    user_guide = '''# User Guide

## Using the AI Chatbot

1. Click the chat icon (💬) in the bottom-right corner
2. Type your question
3. Press Enter to send
4. The AI will respond with helpful information

### Example Questions:
- "What are your opening hours?"
- "Do you have vegetarian options?"
- "How do I book an event?"
- "What's on the menu today?"

## Booking an Event

1. Browse events on the homepage
2. Click "Book Now" on desired event
3. Fill in your details
4. Submit booking
5. Receive confirmation email
'''

    with open(f"{output_dir}/USER_GUIDE.md", "w") as f:
        f.write(user_guide)

    return {
        "readme": f"{output_dir}/README.md",
        "api_docs": f"{output_dir}/API_DOCS.md",
        "deployment": f"{output_dir}/DEPLOYMENT.md",
        "user_guide": f"{output_dir}/USER_GUIDE.md"
    }


async def create_deployment_config(design: Dict, output_dir: str) -> Dict:
    """Create deployment configuration"""

    # Dockerfile for backend
    backend_dockerfile = '''FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 4000

CMD ["npm", "start"]
'''

    os.makedirs(f"{output_dir}/backend", exist_ok=True)
    with open(f"{output_dir}/backend/Dockerfile", "w") as f:
        f.write(backend_dockerfile)

    # Dockerfile for frontend
    frontend_dockerfile = '''FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
'''

    os.makedirs(f"{output_dir}/frontend", exist_ok=True)
    with open(f"{output_dir}/frontend/Dockerfile", "w") as f:
        f.write(frontend_dockerfile)

    return {
        "backend_dockerfile": f"{output_dir}/backend/Dockerfile",
        "frontend_dockerfile": f"{output_dir}/frontend/Dockerfile",
        "docker_compose": f"{output_dir}/docker-compose.yml"
    }


def format_requirements_doc(requirements: Dict) -> str:
    """Format requirements as markdown"""
    doc = "# Requirements Document\n\n"
    doc += f"## Original Requirement\n{requirements['raw_requirement']}\n\n"

    doc += "## Functional Requirements\n\n"
    for req in requirements['functional']:
        doc += f"### {req['id']}: {req['name']}\n{req['description']}\n\n"

    doc += "## Non-Functional Requirements\n\n"
    for req in requirements['non_functional']:
        doc += f"### {req['id']}: {req['category']}\n{req['requirement']}\n\n"

    return doc


def format_architecture_doc(design: Dict) -> str:
    """Format architecture as markdown"""
    doc = "# Architecture Document\n\n"
    doc += f"## Architecture Type\n{design['architecture']['type']}\n\n"
    doc += f"## Pattern\n{design['architecture']['pattern']}\n\n"

    doc += "## Technology Stack\n\n"
    for tech in design['tech_stack']:
        doc += f"- **{tech['component']}**: {tech['technology']}\n"

    doc += "\n## Database Schema\n\n"
    for table in design.get('database_schema', {}).get('tables', []):
        doc += f"### {table['name']}\n"
        doc += f"Columns: {', '.join(table['columns'])}\n\n"

    return doc


def get_project_structure(output_dir: str) -> Dict:
    """Get project directory structure"""
    structure = {
        "root": output_dir,
        "backend": f"{output_dir}/backend",
        "frontend": f"{output_dir}/frontend",
        "docs": [
            "README.md",
            "ARCHITECTURE.md",
            "REQUIREMENTS.md",
            "API_DOCS.md",
            "DEPLOYMENT.md",
            "USER_GUIDE.md"
        ]
    }
    return structure


def print_project_tree(structure: Dict):
    """Print project tree"""
    print(f"\n{structure['root']}/")
    print("├── backend/")
    print("│   ├── src/")
    print("│   │   ├── index.js")
    print("│   │   ├── routes/")
    print("│   │   │   ├── events.js")
    print("│   │   │   ├── bookings.js")
    print("│   │   │   └── chat.js")
    print("│   │   └── services/")
    print("│   │       └── chatbot.js")
    print("│   ├── package.json")
    print("│   ├── .env.example")
    print("│   └── Dockerfile")
    print("├── frontend/")
    print("│   ├── src/")
    print("│   │   ├── app/")
    print("│   │   │   └── page.tsx")
    print("│   │   └── components/")
    print("│   │       ├── ChatBot.tsx")
    print("│   │       └── EventList.tsx")
    print("│   ├── package.json")
    print("│   ├── next.config.js")
    print("│   └── Dockerfile")
    print("├── .github/")
    print("│   └── workflows/")
    print("│       └── ci.yml")
    print("├── docker-compose.yml")
    print("├── README.md")
    print("├── ARCHITECTURE.md")
    print("├── REQUIREMENTS.md")
    print("├── API_DOCS.md")
    print("├── DEPLOYMENT.md")
    print("└── USER_GUIDE.md\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """
    Example usage of the code generator
    """

    result = await generate_code_from_requirement(
        requirement="Create an improved website like mannam.co.uk, with advanced SEO optimization and AI Chatbot (OpenAI)",
        output_dir="./generated_restaurant_website",
        reference_url="https://mannam.co.uk",
        api_keys={"openai": "your-api-key-here"},
        enable_autonomous_agents=False
    )

    if result['success']:
        print("\n✅ Code generation successful!")
        print(f"\n📁 Project location: {result['project_dir']}")
        print(f"\n📝 Generated {len(result['generated_files'])} files")


if __name__ == "__main__":
    asyncio.run(main())
