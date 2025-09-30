"""
Django management command to create realistic demo data for context injection.

This command creates:
- Sample users
- Knowledge bases with namespaces
- Articles with various tags and content
- Documents with metadata
- Projects with team members
- All properly linked for context injection demonstrations
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Create realistic demo data for context injection demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing demo data before creating new data',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of demo users to create',
        )
        parser.add_argument(
            '--articles',
            type=int,
            default=15,
            help='Number of demo articles to create',
        )
        parser.add_argument(
            '--projects',
            type=int,
            default=8,
            help='Number of demo projects to create',
        )

    def handle(self, *args, **options):
        from django.contrib.auth.models import User
        from django_ollama.models import Namespace, KnowledgeBase
        from knowledge_demo.models import Article, Document, Project

        if options['clear']:
            self.stdout.write('🗑️  Clearing existing demo data...')
            self.clear_demo_data()

        self.stdout.write('🚀 Creating demo data for context injection...')

        # Create users
        users = self.create_users(options['users'])
        self.stdout.write(f'✅ Created {len(users)} demo users')

        # Create namespaces and knowledge bases
        namespaces = self.create_namespaces_and_knowledge_bases(users)
        self.stdout.write(f'✅ Created {len(namespaces)} namespaces with knowledge bases')

        # Create projects
        projects = self.create_projects(users, namespaces, options['projects'])
        self.stdout.write(f'✅ Created {len(projects)} demo projects')

        # Create articles
        articles = self.create_articles(users, projects, options['articles'])
        self.stdout.write(f'✅ Created {len(articles)} demo articles')

        # Create documents
        documents = self.create_documents(users, projects)
        self.stdout.write(f'✅ Created {len(documents)} demo documents')

        self.stdout.write('\n🎉 Demo data creation completed!')
        self.stdout.write('\n📊 Summary:')
        self.stdout.write(f'   👥 Users: {User.objects.count()}')
        self.stdout.write(f'   🏢 Namespaces: {Namespace.objects.count()}')
        self.stdout.write(f'   📚 Knowledge Bases: {KnowledgeBase.objects.count()}')
        self.stdout.write(f'   📄 Articles: {Article.objects.count()}')
        self.stdout.write(f'   📁 Documents: {Document.objects.count()}')
        self.stdout.write(f'   🎯 Projects: {Project.objects.count()}')
        self.stdout.write('\n🌐 Visit /streaming-chat/ to test the context injection!')

    def clear_demo_data(self):
        """Clear existing demo data."""
        from django_ollama.models import Namespace
        from knowledge_demo.models import Article, Document, Project

        Article.objects.all().delete()
        Document.objects.all().delete()
        Project.objects.all().delete()
        # Don't delete all knowledge bases and namespaces as they might be system ones
        demo_namespaces = Namespace.objects.filter(name__startswith='demo-')
        demo_namespaces.delete()

    def create_users(self, count):
        """Create demo users."""
        from django.contrib.auth.models import User

        users = []
        demo_users_data = [
            ('alice_dev', 'Alice Johnson', 'alice@example.com'),
            ('bob_pm', 'Bob Smith', 'bob@example.com'),
            ('carol_design', 'Carol Williams', 'carol@example.com'),
            ('david_ops', 'David Brown', 'david@example.com'),
            ('eve_qa', 'Eve Davis', 'eve@example.com'),
            ('frank_data', 'Frank Miller', 'frank@example.com'),
            ('grace_ui', 'Grace Wilson', 'grace@example.com'),
            ('henry_backend', 'Henry Moore', 'henry@example.com'),
        ]

        for i in range(min(count, len(demo_users_data))):
            username, full_name, email = demo_users_data[i]
            first_name, last_name = full_name.split(' ', 1)

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                }
            )
            if created:
                user.set_password('demo123')
                user.save()
            users.append(user)

        return users

    def create_namespaces_and_knowledge_bases(self, users):
        """Create demo namespaces with knowledge bases."""
        from django_ollama.models import Namespace, KnowledgeBase

        namespaces_data = [
            ('demo-frontend', 'Frontend Development', 'Frontend team knowledge and resources'),
            ('demo-backend', 'Backend Services', 'Backend API and service documentation'),
            ('demo-devops', 'DevOps & Infrastructure', 'Infrastructure and deployment resources'),
            ('demo-design', 'UX/UI Design', 'Design systems and user experience resources'),
            ('demo-public', 'Public Resources', 'Publicly accessible documentation and guides'),
        ]

        namespaces = []
        for ns_name, display_name, description in namespaces_data:
            namespace, created = Namespace.objects.get_or_create(
                name=ns_name,
                defaults={
                    'description': description,
                    'owner': random.choice(users),
                    'slug': ns_name.replace('demo-', '').replace('-', '_'),
                }
            )

            # Create knowledge base for this namespace
            kb, kb_created = KnowledgeBase.objects.get_or_create(
                name=f"{display_name} Knowledge Base",
                namespace=namespace,
                defaults={
                    'description': f"Knowledge base for {description.lower()}",
                }
            )

            namespaces.append((namespace, kb))

        return namespaces

    def create_projects(self, users, namespaces, count):
        """Create demo projects with knowledge bases."""
        from django_ollama.models import KnowledgeBase
        from knowledge_demo.models import Project

        projects_data = [
            ('E-commerce Platform', 'Modern e-commerce platform with microservices architecture', True),
            ('Mobile Banking App', 'Secure mobile banking application with biometric authentication', False),
            ('Content Management System', 'Headless CMS for enterprise content management', True),
            ('Real-time Analytics Dashboard', 'Live analytics dashboard with streaming data processing', False),
            ('AI-Powered Chatbot', 'Intelligent customer service chatbot with NLP capabilities', True),
            ('Inventory Management System', 'Warehouse and inventory tracking system', False),
            ('Social Media Platform', 'Decentralized social media platform with privacy focus', True),
            ('Video Streaming Service', 'Netflix-style video streaming platform', False),
            ('IoT Device Management', 'Platform for managing IoT devices and sensor data', True),
            ('Learning Management System', 'Online education platform with interactive features', True),
        ]

        projects = []
        for i in range(min(count, len(projects_data))):
            name, description, is_public = projects_data[i]
            owner = random.choice(users)
            namespace, kb = random.choice(namespaces)

            # Create a dedicated knowledge base for this project
            project_kb = KnowledgeBase.objects.create(
                name=f"{name} Knowledge Base",
                namespace=namespace,
                description=f"Knowledge base for {name} project",
            )

            project = Project.objects.create(
                name=name,
                description=description,
                owner=owner,
                knowledge_base=project_kb,
                is_public=is_public,
            )

            # Add random team members
            available_members = [u for u in users if u != owner]
            team_size = random.randint(1, min(3, len(available_members))) if available_members else 0
            team_members = random.sample(available_members, team_size) if team_size > 0 else []
            project.team_members.set(team_members)

            projects.append(project)

        return projects

    def create_articles(self, users, projects, count):
        """Create demo articles with realistic content."""
        from knowledge_demo.models import Article

        article_templates = [
            # Technical Documentation
            ("API Authentication Guide", "authentication, security, api", """
# API Authentication Guide

This guide covers the authentication mechanisms used in our API.

## Overview
Our API uses JWT (JSON Web Tokens) for authentication. Each request must include a valid token in the Authorization header.

## Getting a Token
To obtain a token, send a POST request to `/auth/login` with your credentials:

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

## Using the Token
Include the token in your requests:

```
Authorization: Bearer your_jwt_token_here
```

## Token Expiration
Tokens expire after 24 hours. Refresh tokens are valid for 7 days.

## Security Best Practices
- Always use HTTPS in production
- Store tokens securely
- Implement proper token refresh logic
- Never log authentication tokens
            """),

            ("Database Schema Design", "database, schema, design", """
# Database Schema Design

This document outlines our database schema design principles and current structure.

## Design Principles
1. **Normalization**: Follow 3NF where possible
2. **Performance**: Denormalize for critical queries
3. **Scalability**: Design for horizontal scaling
4. **Maintainability**: Clear naming conventions

## Core Tables

### Users Table
- `id`: Primary key (UUID)
- `username`: Unique identifier
- `email`: Contact information
- `created_at`: Timestamp
- `updated_at`: Auto-updating timestamp

### Projects Table
- `id`: Primary key (UUID)
- `name`: Project identifier
- `description`: Project details
- `owner_id`: Foreign key to Users
- `status`: Enum (active, archived, deleted)

## Relationships
- One-to-many: User → Projects
- Many-to-many: Users ↔ Project Members
- One-to-one: Project → Knowledge Base

## Indexing Strategy
Critical indexes on:
- User.username (unique)
- User.email (unique)
- Project.owner_id
- Project.status
            """),

            ("Frontend Component Library", "frontend, components, react", """
# Frontend Component Library

Our component library provides reusable UI components for consistent user interfaces.

## Installation
```bash
npm install @company/ui-components
```

## Usage
```jsx
import { Button, Card, Modal } from '@company/ui-components';

function MyComponent() {
  return (
    <Card>
      <Button variant="primary" onClick={handleClick}>
        Click me
      </Button>
    </Card>
  );
}
```

## Components

### Button
- **Variants**: primary, secondary, danger, ghost
- **Sizes**: small, medium, large
- **States**: loading, disabled

### Card
- **Layout**: Flexible container with padding
- **Elevation**: Shadow levels 0-4
- **Variants**: default, outlined

### Modal
- **Backdrop**: Configurable backdrop behavior
- **Size**: small, medium, large, fullscreen
- **Animation**: Smooth enter/exit transitions

## Theming
Components support custom themes through CSS variables:

```css
:root {
  --color-primary: #007bff;
  --color-secondary: #6c757d;
  --border-radius: 4px;
  --spacing-unit: 8px;
}
```

## Accessibility
All components follow WCAG 2.1 AA guidelines:
- Keyboard navigation
- Screen reader support
- High contrast compatibility
- Focus management
            """),

            ("Deployment Pipeline", "devops, ci/cd, deployment", """
# Deployment Pipeline

Our automated deployment pipeline ensures reliable and consistent deployments.

## Pipeline Stages

### 1. Source Control
- **Git**: Feature branch workflow
- **PR Reviews**: Required before merge
- **Branch Protection**: Main branch protection rules

### 2. Build Stage
```yaml
build:
  script:
    - npm ci
    - npm run build
    - npm run test
  artifacts:
    paths:
      - dist/
```

### 3. Testing
- **Unit Tests**: Jest + React Testing Library
- **Integration Tests**: Cypress
- **Code Coverage**: Minimum 80% required
- **Security Scan**: SAST + dependency check

### 4. Staging Deployment
- **Environment**: staging.company.com
- **Database**: Staging database with anonymized data
- **Monitoring**: Full monitoring stack

### 5. Production Deployment
- **Blue-Green**: Zero-downtime deployments
- **Rollback**: Automated rollback on failure
- **Health Checks**: Post-deployment verification

## Environment Variables
```bash
# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# API Keys
STRIPE_SECRET_KEY=sk_...
SENDGRID_API_KEY=SG...

# Feature Flags
FEATURE_NEW_DASHBOARD=true
FEATURE_BETA_ANALYTICS=false
```

## Monitoring
- **Uptime**: Pingdom
- **Performance**: New Relic
- **Logs**: ELK Stack
- **Alerts**: PagerDuty integration
            """),

            ("Security Guidelines", "security, guidelines, best-practices", """
# Security Guidelines

This document outlines security best practices for our development team.

## Code Security

### Input Validation
- **Sanitize**: All user inputs
- **Validate**: Data types and ranges
- **Escape**: Output for XSS prevention
- **Parameterize**: Database queries

### Authentication & Authorization
- **Strong Passwords**: Minimum 12 characters
- **2FA**: Required for admin accounts
- **Session Management**: Secure session handling
- **JWT**: Proper token validation

### Data Protection
- **Encryption**: AES-256 for sensitive data
- **TLS**: 1.3 for all communications
- **Key Management**: HSM for production keys
- **Data Classification**: Sensitive data identification

## Infrastructure Security

### Access Control
- **Principle of Least Privilege**: Minimal required access
- **Role-Based Access**: RBAC implementation
- **Regular Reviews**: Quarterly access audits
- **Privileged Accounts**: Separate admin accounts

### Network Security
- **Firewalls**: Default deny rules
- **VPN**: Required for remote access
- **Segmentation**: Network isolation
- **Monitoring**: Intrusion detection

### Cloud Security
- **IAM Policies**: Granular permissions
- **Encryption**: At rest and in transit
- **Logging**: CloudTrail enabled
- **Compliance**: SOC 2 Type II

## Incident Response
1. **Detection**: Automated monitoring alerts
2. **Analysis**: Security team assessment
3. **Containment**: Isolate affected systems
4. **Eradication**: Remove threat completely
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Post-incident review
            """),

            ("Performance Optimization Guide", "performance, optimization, monitoring", """
# Performance Optimization Guide

This guide covers performance optimization strategies for our applications.

## Frontend Optimization

### Bundle Size
- **Code Splitting**: Dynamic imports for routes
- **Tree Shaking**: Remove unused code
- **Compression**: Gzip/Brotli compression
- **CDN**: Static asset delivery

### Runtime Performance
- **Memoization**: React.memo for components
- **Virtualization**: Large list rendering
- **Lazy Loading**: Images and components
- **Debouncing**: Input handling

### Metrics
- **Core Web Vitals**:
  - LCP < 2.5s (Largest Contentful Paint)
  - FID < 100ms (First Input Delay)
  - CLS < 0.1 (Cumulative Layout Shift)

## Backend Optimization

### Database
- **Indexing**: Query optimization
- **Connection Pooling**: Efficient connections
- **Query Analysis**: Slow query identification
- **Caching**: Redis for frequently accessed data

### API Performance
- **Pagination**: Large dataset handling
- **Compression**: Response compression
- **Caching Headers**: HTTP caching
- **Rate Limiting**: Prevent abuse

### Monitoring
```javascript
// Performance tracking
const performanceObserver = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.entryType === 'navigation') {
      console.log('Page load time:', entry.duration);
    }
  }
});

performanceObserver.observe({entryTypes: ['navigation']});
```

## Infrastructure

### Auto Scaling
- **Horizontal**: Pod autoscaling
- **Vertical**: Resource adjustment
- **Predictive**: ML-based scaling
- **Cost Optimization**: Right-sizing instances

### Load Balancing
- **Algorithm**: Least connections
- **Health Checks**: Endpoint monitoring
- **Session Affinity**: Sticky sessions
- **SSL Termination**: Load balancer SSL

### Caching Strategy
- **CDN**: Global content distribution
- **Application Cache**: In-memory caching
- **Database Cache**: Query result caching
- **Browser Cache**: Client-side caching
            """),
        ]

        articles = []
        tags_pool = [
            'frontend', 'backend', 'api', 'database', 'security', 'performance',
            'deployment', 'testing', 'documentation', 'architecture', 'ui/ux',
            'devops', 'monitoring', 'optimization', 'best-practices', 'tutorial',
            'guide', 'troubleshooting', 'configuration', 'integration'
        ]

        for i in range(count):
            # Cycle through templates and add variations
            template_idx = i % len(article_templates)
            title_base, base_tags, content = article_templates[template_idx]

            # Add variation to title if cycling
            if i >= len(article_templates):
                cycle = i // len(article_templates) + 1
                title = f"{title_base} v{cycle}"
            else:
                title = title_base

            # Select random author and project
            author = random.choice(users)
            project = random.choice(projects) if projects else None

            # Create tag list
            article_tags = base_tags.split(', ')
            # Add some random additional tags
            additional_tags = random.sample(tags_pool, random.randint(1, 3))
            all_tags = list(set(article_tags + additional_tags))

            article = Article.objects.create(
                title=title,
                content=content.strip(),
                author=author,
                knowledge_base=project.knowledge_base if project else None,
                tags=all_tags,
            )

            articles.append(article)

        return articles

    def create_documents(self, users, projects):
        """Create demo documents with metadata."""
        from knowledge_demo.models import Document

        documents_data = [
            ("Technical Specification.pdf", "Complete technical specification document", "pdf"),
            ("API Documentation.md", "REST API endpoint documentation", "md"),
            ("Database Schema.sql", "Database creation and migration scripts", "sql"),
            ("User Manual.docx", "End-user documentation and guides", "docx"),
            ("Architecture Diagram.png", "System architecture overview", "png"),
            ("Test Plan.xlsx", "Comprehensive testing strategy and cases", "xlsx"),
            ("Security Audit Report.pdf", "Security assessment and recommendations", "pdf"),
            ("Performance Metrics.json", "Application performance benchmarks", "json"),
            ("Deployment Guide.md", "Step-by-step deployment instructions", "md"),
            ("Code Review Checklist.txt", "Development team code review guidelines", "txt"),
            ("Meeting Notes Q1.md", "Quarterly team meeting notes and action items", "md"),
            ("Wireframes Collection.zip", "UI/UX wireframes and mockups", "zip"),
            ("Brand Guidelines.pdf", "Company branding and style guide", "pdf"),
            ("Training Materials.pptx", "Team training presentations", "pptx"),
            ("Backup Procedures.md", "Data backup and recovery procedures", "md"),
        ]

        documents = []
        for name, description, doc_type in documents_data:
            uploader = random.choice(users)
            project = random.choice(projects) if projects else None

            document = Document.objects.create(
                name=name,
                description=description,
                uploaded_by=uploader,
                knowledge_base=project.knowledge_base if project else None,
                document_type=doc_type,
                file_size=random.randint(1024, 10 * 1024 * 1024),  # 1KB to 10MB
            )

            documents.append(document)

        return documents