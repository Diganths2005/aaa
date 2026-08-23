# TaxWise Development Roadmap

## Phase 1: Foundation (Current - Week 1-2)
### Authentication & Dashboard
- [x] Login/Signup flow
- [x] JWT-based authentication
- [x] Dashboard view
- [x] Tax Profile form (6-step wizard)
- [x] Personal information collection
- [x] Residential status & employment
- [x] Income details
- [x] Investments & deductions
- [x] Tax & bank details
- [x] Document upload placeholder

**Milestone**: Login → Dashboard → Tax Profile → Save

---

## Document Intelligence + RAG (Optional, Architecture Added)

Document upload is never required for TaxWise, Tax Engine, or ITR workflows. The current implementation adds isolated document metadata, authenticated ownership checks, and processor/retriever interfaces. It does not add an LLM, OCR provider, vector database, or automatic profile updates.

### Planned stages
1. [x] Optional PDF upload entry point
2. [ ] PDF text extraction
3. [ ] OCR for scanned PDFs
4. [ ] Document classification
5. [ ] User confirmation (Confirm, Edit, Reject)
6. [x] User document metadata and storage boundary
7. [ ] Official tax knowledge base, versioned by assessment year
8. [ ] Embeddings
9. [ ] Vector search
10. [ ] RAG retrieval with user and assessment-year filters
11. [ ] AI Copilot
12. [ ] Source-aware explanations
13. [ ] Tax-saving recommendations
14. [ ] What-if tax simulations

See [DOCUMENT_INTELLIGENCE.md](DOCUMENT_INTELLIGENCE.md) for the data model, security model, and service contracts.

---

## Phase 2: Tax Engine (Week 3-4)
### Tax Calculation
- [ ] Income aggregation service
- [ ] Deduction validator
- [ ] Standard deduction calculation (80C, 80D, etc.)
- [ ] Taxable income calculation
- [ ] Tax bracket determination
- [ ] Surcharge & cess calculation
- [ ] Tax liability calculator
- [ ] Rebate & relief processor

### ITR Preview
- [ ] Generate ITR form preview
- [ ] Calculate refund/payable amount
- [ ] Display tax summary
- [ ] Generate PDF preview

**Milestone**: Dashboard → File ITR → Preview → Download PDF

---

## Phase 3: ITR Filing (Week 5-6)
### E-Filing Integration
- [ ] NSDL e-filing API integration
- [ ] Form submission
- [ ] Acknowledgment handling
- [ ] Status tracking
- [ ] Resubmission handling

### Document Management
- [ ] Document upload
- [ ] File storage (S3/Cloud)
- [ ] Document validation
- [ ] Compression & optimization
- [ ] Download & viewing

### Filing History
- [ ] Previous filing records
- [ ] Comparison view
- [ ] Amendment filing flow
- [ ] Status tracking

**Milestone**: File ITR → E-File → Track Status

---

## Phase 4: AI Copilot (Week 7-8)
### RAG-Based Support
- [ ] Setup LLM (Google Gemini API)
- [ ] Tax knowledge base indexing
- [ ] Vector database (Pinecone/Weaviate)
- [ ] Retrieval augmented generation (RAG)

### Copilot Features
- [ ] Real-time guidance during form filling
- [ ] Question answering
- [ ] Document processing & analysis
- [ ] Form auto-fill suggestions
- [ ] Error explanation

### Integration
- [ ] Copilot chat widget
- [ ] Context-aware suggestions
- [ ] Multi-turn conversations
- [ ] Session management

**Milestone**: Tax Profile → Copilot Guidance → Auto-Fill

---

## Phase 5: Analytics & Optimization (Week 9-10)
### User Analytics
- [ ] User behavior tracking
- [ ] Form completion metrics
- [ ] Time spent per section
- [ ] Drop-off points analysis

### Performance
- [ ] Frontend optimization
- [ ] Backend caching
- [ ] Database indexing
- [ ] CDN integration

### Admin Dashboard
- [ ] User statistics
- [ ] Filing success rates
- [ ] Error tracking
- [ ] Performance metrics

---

## Phase 6: Advanced Features (Week 11-12)
### Multi-Year Filings
- [ ] Year selection
- [ ] Historical data preservation
- [ ] Comparison & tracking
- [ ] Bulk operations

### Compliance & Audit
- [ ] Audit log
- [ ] Data validation rules
- [ ] Compliance checklist
- [ ] Warning system

### Mobile App
- [ ] React Native app
- [ ] Responsive design
- [ ] Offline support
- [ ] Push notifications

---

## Infrastructure & DevOps
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Docker containerization
- [ ] Kubernetes deployment
- [ ] Monitoring & logging
- [ ] Error tracking (Sentry)
- [ ] Performance monitoring (DataDog)
- [ ] Database backup & recovery
- [ ] Staging environment

---

## Security & Compliance
- [ ] HTTPS/TLS
- [ ] Data encryption (AES-256)
- [ ] PII handling compliance
- [ ] Regular security audits
- [ ] Penetration testing
- [ ] GDPR compliance
- [ ] Privacy policy
- [ ] Terms of service

---

## Timeline Summary
- **Week 1-2**: Foundation ✓
- **Week 3-4**: Tax Engine
- **Week 5-6**: ITR Filing
- **Week 7-8**: AI Copilot
- **Week 9-10**: Analytics
- **Week 11-12**: Advanced Features
- **Ongoing**: DevOps & Security

---

## Current Status: Phase 1 - Foundation
✅ Project structure created
✅ Frontend pages implemented
✅ Backend API routes created
⏳ Database migrations needed
⏳ Testing framework setup
⏳ Deployment configuration

### Next Immediate Steps:
1. Setup PostgreSQL database
2. Install dependencies (npm, pip)
3. Run frontend and backend
4. Test the login → profile flow
5. Fix any bugs
6. Begin Phase 2: Tax Engine
