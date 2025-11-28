# Frontend Templates Collection

This directory contains a comprehensive collection of frontend templates based on industry-leading design patterns and frameworks. These templates enable AI agents to rapidly scaffold high-quality user interfaces by leveraging established design patterns and best-in-class packages.

## Template Classification Framework

Templates are organized into 5 main categories based on their primary purpose and use case:

### 1. Admin Dashboards & Application UIs (4 templates)

Templates for managing data, back-office operations, SaaS applications, CRMs, and monitoring systems.

| Template | Framework | Design System | Best For |
|----------|-----------|---------------|----------|
| **tailwind-admin-dashboard** | React + Tailwind CSS | Tailwind UI | General admin panels, CRUD interfaces |
| **mui-admin-dashboard** | React + MUI | Material Design | Enterprise applications, data-intensive apps |
| **refine-admin-panel** | React + Refine | Customizable | Internal tools, B2B applications |
| **tremor-data-dashboard** | React + Tremor | Tremor | Analytics dashboards, monitoring, KPIs |

### 2. Marketing & Corporate Websites (3 templates)

Templates for public-facing websites focused on user acquisition, product marketing, and brand presence.

| Template | Framework | Design System | Best For |
|----------|-----------|---------------|----------|
| **cruip-landing-page** | Next.js + Tailwind | Cruip | SaaS landing pages, product launches |
| **nextjs-marketing-site** | Next.js | Custom | Corporate websites, content marketing |
| **tailwind-marketing-site** | React + Tailwind | Tailwind UI | Marketing pages, agency websites |

### 3. E-commerce Platforms (3 templates)

Templates for online transactions with product discovery, cart management, and checkout flows.

| Template | Framework | Design System | Best For |
|----------|-----------|---------------|----------|
| **nextjs-commerce** | Next.js | Custom | Headless commerce, high-performance stores |
| **vue-storefront** | Vue.js + Nuxt | Custom | Mobile-first PWA, multi-platform commerce |
| **shopify-headless** | React + Hydrogen | Custom | Custom Shopify storefronts |

### 4. Content, Blogs, & Documentation (4 templates)

Templates for showcasing work, publishing articles, and documentation.

| Template | Framework | Design System | Best For |
|----------|-----------|---------------|----------|
| **ghost-blog** | Ghost CMS | Custom | Professional publishing, newsletters |
| **docusaurus-docs** | Docusaurus | Docusaurus | Technical documentation, API docs |
| **astro-portfolio** | Astro | Custom | Personal portfolios, creative showcases |
| **gatsby-blog** | Gatsby + React | Custom | Content-heavy blogs, publications |

### 5. Foundational UI Systems (5 templates)

Base component libraries and design systems that can be used to build custom applications.

| Template | Framework | Design System | Best For |
|----------|-----------|---------------|----------|
| **mui-component-library** | React + MUI | Material Design | Enterprise component libraries |
| **chakra-ui-starter** | React + Chakra UI | Chakra UI | Accessible applications, rapid prototyping |
| **tailwind-starter** | React + Tailwind | Tailwind | Custom designs, utility-first approach |
| **ant-design-enterprise** | React + Ant Design | Ant Design | Business applications, enterprise systems |
| **radix-ui-system** | React + Radix UI | Custom | Headless components, complete design control |

## Classification Dimensions

AI agents should analyze requirements along these dimensions to select the optimal template:

### Purpose/Use Case
- **Data Management**: Admin dashboards (Tailwind, MUI, Refine)
- **Product Marketing**: Landing pages (Cruip, Next.js Marketing)
- **Online Sales**: E-commerce (Next.js Commerce, Vue Storefront, Shopify)
- **Documentation**: Documentation sites (Docusaurus)
- **Content Publishing**: Blogs (Ghost, Gatsby, Astro)
- **Component Libraries**: UI Systems (MUI, Chakra, Tailwind, Ant Design, Radix)

### Technology Stack
- **React/Next.js**: 11 templates
- **Vue/Nuxt**: 1 template
- **Specialized**: Ghost, Docusaurus, Astro, Gatsby

### Design System
- **Material Design**: MUI templates (2)
- **Tailwind CSS**: 5 templates
- **Ant Design**: 1 template
- **Custom/Flexible**: 7 templates
- **Specialized**: Tremor, Chakra UI, Radix UI

### Complexity Level
- **Simple**: Tailwind Starter, Astro Portfolio, Tailwind Marketing
- **Intermediate**: Most admin and marketing templates
- **Advanced**: Refine, MUI Admin, E-commerce templates

## Template Structure

Each template follows this standard structure:

```
template-name/
├── manifest.yaml          # Template metadata and configuration
├── src/                   # Source code
├── docs/                  # Documentation
│   ├── QUICKSTART.md     # Getting started guide
│   ├── API.md            # API documentation (if applicable)
│   └── ...
├── examples/             # Example implementations
└── README.md            # Template-specific README
```

## Using These Templates

### With MAESTRO CLI

```bash
# List available templates
maestro-template list

# Create a new project from a template
maestro-template init --template=tailwind-admin-dashboard

# Validate a template
cd template-directory
maestro-template validate

# Register a template
maestro-template register
```

### Via API

```bash
# Get all frontend templates
curl http://localhost:9600/api/v1/templates?category=frontend

# Get a specific template
curl http://localhost:9600/api/v1/templates/{template-id}

# Download a template
curl http://localhost:9600/api/v1/templates/{template-id}/download
```

## Template Features

All templates include:

- ✅ **Production-ready**: Battle-tested patterns and best practices
- ✅ **TypeScript support**: Type safety and better developer experience
- ✅ **Responsive design**: Mobile-first, works on all devices
- ✅ **Accessibility**: WCAG 2.1 AA compliant (where applicable)
- ✅ **SEO optimized**: Meta tags, structured data, sitemaps
- ✅ **Performance**: Optimized for Core Web Vitals
- ✅ **Documentation**: Comprehensive guides and examples
- ✅ **Customizable**: Easy to adapt to specific needs

## Quality Tiers

Templates are categorized by quality tier:

- **Gold**: Industry-leading templates (Next.js Commerce, MUI, Docusaurus)
- **Silver**: High-quality, well-maintained templates (Most templates)
- **Bronze**: Good starting points, may need customization
- **Standard**: Basic templates for rapid prototyping

## Contributing

To add a new frontend template:

1. Create a new directory under `frontend-templates/`
2. Add a `manifest.yaml` file following the schema
3. Include README, docs, and examples
4. Validate with `maestro-template validate`
5. Register with the central registry

## Integration with AI Agents

AI agents can use these templates by:

1. **Analyzing requirements**: Parse user needs to identify use case
2. **Template selection**: Match requirements to classification dimensions
3. **Customization**: Use placeholders to configure the template
4. **Generation**: Scaffold the project with selected options
5. **Post-processing**: Run hooks and installation scripts

## Version History

- **v1.0.0** (2025-10-04): Initial collection with 19 templates across 5 categories

## License

All templates are released under the MIT License unless otherwise specified in individual template manifests.

## Support

For issues or questions:
- Check individual template documentation
- Review the MAESTRO Templates documentation
- Open an issue in the project repository
