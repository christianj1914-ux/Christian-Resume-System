# Supply Chain and Cost Modeling
### A study guide built around the one skill that separates strategic buyers from average ones.

**Bottom line up front:** the LinkedIn post is right. Tools change (SAP Ariba, dashboards, whatever is next), but the fundamentals of cost modeling do not. If you can break down cost drivers, analyze supplier pricing, benchmark the market, and build negotiation levers, you understand most of what matters in procurement. This guide teaches that first, then maps it to the rest of the supply chain and to the defense and aerospace context the post names.

**Why this fits you:** East West Manufacturing is a contract manufacturer, so you have already lived where cost flows: materials, labor, overhead, and the tradeoffs between operations, finance, and engineering. You have also run the ERP systems (Aptean, Epicor) where cost, inventory, and sourcing data live. That is real, ownable evidence for a procurement or supply chain analyst lane. This adds a target lane to your search, alongside the AI and consulting paths.

---

## 1. Cost modeling: the core skill

Cost modeling means building your own independent estimate of what something should cost, from the ground up, instead of just reacting to the supplier's quoted price. It changes a negotiation from pressure-based ("give me 10% off") to evidence-based ("your overhead allocation looks 8 points high against market"). There are three frameworks worth knowing cold.

### A. Should-cost (bottom-up cost build)
A buyer's independent estimate of what a part should cost to make, built from its pieces: **materials + labor + manufacturing overhead + other costs + margin.**

**Worked example (memorize this shape):**
- Raw materials: $55
- Labor: $30 (1 hour at $30/hour)
- Manufacturing overhead: $25
- **Base cost: $110**
- Supplier margin at 15%: $16.50
- **Should-cost price: $126.50**

If the supplier quotes $150, you now have a specific, defensible conversation: where is the extra $23.50, and is it in a line you can challenge (labor, overhead, margin) or one that is market-driven (raw material)?

### B. Total Cost of Ownership (TCO)
Price is only the tip. TCO captures the whole life of the purchase: **acquisition + operation + maintenance + logistics + risk + end-of-life (disposal).** A common short form is: **TCO = Purchase Price + Maintenance + Operating Cost + Risk Cost.**

**Why it matters:** a cheaper unit price often loses on TCO once you add downtime, maintenance, freight, quality failures, and disposal. Organizations that buy on TCO instead of price alone report roughly 20 to 35% better cost outcomes.

**Worked example (Supplier A vs B, over 3 years):**
| Cost element | Supplier A | Supplier B |
|---|---|---|
| Purchase price | $100,000 | $115,000 |
| Maintenance (3 yr) | $40,000 | $18,000 |
| Downtime / risk | $25,000 | $8,000 |
| Freight / logistics | $6,000 | $5,000 |
| **TCO** | **$171,000** | **$146,000** |

Supplier A is $15,000 cheaper on the sticker and $25,000 more expensive to own. That table is the whole argument.

### C. Parametric and activity-based costing (know the names)
- **Parametric:** estimate cost from a driver using a statistical relationship (for example, cost per pound of a machined aluminum part, or cost scaling with horsepower or lines of code). Fast for early estimates and common in aerospace and defense.
- **Activity-based costing (ABC):** allocate overhead to products by the activities they actually consume, rather than a flat rate. It exposes where hidden cost really lives.

### The negotiation levers (what to actually push on)
Not all cost lines are equally negotiable. In order of usual leverage:
1. **Margin** every supplier has one; knowing a reasonable range is leverage.
2. **Labor and overhead** often reflect the supplier's efficiency, which is negotiable, especially with volume or process change.
3. **Logistics** freight terms, mode, consolidation, Incoterms.
4. **Materials** usually the least negotiable, because they are market-driven, but volume, substitution, and index-based pricing help.

---

## 2. How cost connects the whole function
The post's deeper point: master how cost flows and you see how everything else connects.
- **Sourcing** picks suppliers on total cost and value, not sticker price.
- **Contracts** lock in the cost structure: price mechanisms, index clauses, service levels, risk allocation.
- **Supplier performance** protects the cost you negotiated (quality, on-time, cost of poor quality).
- **Category management** applies cost modeling across a whole spend category to find structural savings.

## 3. Supply chain fundamentals (the SCOR map)
The standard model of a supply chain has six pieces. Learn this frame and everything hangs off it:
- **Plan** demand planning, S&OP, inventory strategy.
- **Source** procurement, supplier selection, cost modeling, contracts.
- **Make** production, capacity, quality, Lean.
- **Deliver** logistics, warehousing, distribution, fulfillment.
- **Return** reverse logistics, warranty, recalls.
- **Enable** the data, systems (ERP, Ariba), and governance across all of it.

## 4. Contract lifecycle and supplier risk
- **Contract lifecycle management (CLM):** request, author, negotiate, approve, execute, then manage obligations, renewals, and amendments. "Contract lifecycle optimization" (the Raytheon example) means shortening cycle time and capturing more value across those stages.
- **Supplier risk management:** assess and monitor financial health, single-source exposure, geographic and geopolitical risk, capacity, quality, and cyber. Defense adds compliance and security risk on top.

## 5. Defense and aerospace context (Lockheed, Boeing, Raytheon)
- **FAR / DFARS:** the Federal Acquisition Regulation and its Defense supplement govern how the government and its contractors buy. Buyers must document cost and price analysis, flow down clauses to suppliers, and follow strict compliance (including CMMC-style cybersecurity for the defense supply base).
- **SAP Ariba:** a leading source-to-pay platform (sourcing, contracts, supplier management, procurement). Know it as a category of tool, not a skill in itself.
- **Cost avoidance vs cost savings (the Boeing example):** savings reduce a budgeted spend; cost avoidance prevents a future increase (a price hike you negotiated away, a spec change that dodged a cost). Both count; know the difference.
- **Lean supply (Boeing):** eliminate waste across the supply base, reduce inventory and lead time, pull-based flow.
- **Defense sourcing compliance (Raytheon):** approved suppliers, country-of-origin rules, ITAR/EAR export controls, and auditable cost justification.

---

## 6. What to study (videos first, then courses, then books)

### Videos and channels (start here)
- **"Should-Cost Analysis: TCO vs Price in Procurement"** (YouTube, 2026) a direct, current explainer of the exact core skill.
- **Procurement Tactics** (YouTube channel and blog, procurementtactics.com) practical guides on cost breakdown, should-cost, TCO, and negotiation. Excellent free starting point.
- **CIPS** (cips.org Intelligence Hub and YouTube) authoritative short pieces on TCO, cost management, and category management.
- **ASCM / APICS** content and the "ASCM vs ISM certification" comparison video for the certification landscape.
- **MITx CTL supply chain lectures** (Chris Caplice, on edX and YouTube) rigorous fundamentals, free to audit.

### Courses
- **MITx MicroMasters in Supply Chain Management** (edX, free to audit) the gold-standard online fundamentals.
- **Coursera: Supply Chain Management Specialization** (Rutgers) broad, accessible, with a procurement course.
- **Udemy: "Analyzing Costs Using Total Cost of Ownership"** and should-cost modeling courses hands-on and cheap.
- **Georgia Tech Procurement and Supply Management (PSM) certificates** category management, sourcing, contracting, negotiation.
- **Class Central** aggregates 90+ free and paid TCO and cost courses; good for browsing.

### Books
- **Purchasing and Supply Chain Management** (Monczka et al.) the standard procurement textbook.
- **Supply Chain Management: Strategy, Planning, and Operation** (Chopra and Meindl) the standard supply chain textbook.
- **Negotiation for Procurement and Supply Chain Professionals** (Jonathan O'Brien) and his **Category Management in Purchasing**.

### Certifications (pick by target lane)
- **CPSM** (ISM) the US gold standard for supply management; an updated version releases fall 2026.
- **CSCP** (ASCM/APICS) end-to-end supply chain; strong general credential.
- **CPIM** (ASCM) production and inventory focus, best for manufacturing-heavy roles (fits your East West background).
- **CIPS** (Levels 2 to 6) the global procurement standard, strongest in Europe, the Middle East, and Africa.
- Certified professionals see roughly a 10 to 20% salary premium at equal seniority.

---

## 7. Practice exercises (do these, do not just read)
1. **Build a should-cost model** for something physical you know: pick a product, estimate its material, labor, overhead, and a reasonable margin, and land on a should-cost price. Then find its real price and explain the gap.
2. **Build a TCO comparison** of two options (two laptops, two machines, two suppliers) over three years, including maintenance, downtime, and disposal. Decide which wins and why.
3. **Name three negotiation levers** for a real quote and the evidence you would bring to each.

## 8. How to talk about it in an interview (your top-down voice)
Lead with the cost driver and the leverage, then the proof. For example: "The biggest lever on that spend was overhead allocation, not unit price, so I built a should-cost model, benchmarked the labor rate, and reset the target, which took X out of the quote." That is meat-first, and it signals strategic thinking instantly. Tie your East West and ERP experience to it: you have seen cost, inventory, and sourcing data flow through the system, which is exactly where cost modeling lives.

---
*Added to your Study folder alongside the learning guide, the workbook, and How_I_Think. Tell me if you want this folded into the main learning path as a Supply Chain track with flashcards, or built into a printable Word one-pager.*

## Sources
- Total Cost of Ownership models and courses: procurementtactics.com; ISM (ism.ws); CIPS (cips.org); Class Central (classcentral.com).
- Should-cost model and cost breakdown: procurementtactics.com; precoro.com; controlhub.com; DFMA (dfma.com).
- Certifications: ISM CPSM (ismworld.org); ASCM/APICS CSCP and CPIM; CIPS; Georgia Tech SCL (scl.gatech.edu).
