<!-- sfsales · from 01-business-context-domain.md -->
## 🎯 Quick Scenario Guide

| If user asks for... | Then use... | Key filters & considerations |
|-------------------|------------|---------------------------|
| "Sales pipeline by quarter" | `opportunity`, `opportunity_history` | Filter by fiscal periods, exclude deleted |
| "Top performing sales reps" | `user`, `opportunity`, `territory` | Focus on won deals and pipeline generation |
| "Account penetration analysis" | `account`, `opportunity`, `contact` | Multi-opportunity accounts and relationship depth |
| "Product attach rates" | `product`, `opportunity_product` | Cross-sell and bundle analysis |
| "Territory coverage gaps" | `territory`, `account`, `user` | Geographic and account assignment coverage |
| "Partner channel performance" | `opportunity_partner`, `account` | Channel attribution and partner-driven revenue |

## 🔧 Key Validation Patterns

### Sales Performance Validation
- **Win Rates**: Typically 15-35% for enterprise B2B sales
- **Average Deal Size**: Should align with company's target market and products
- **Sales Cycle Length**: 3-18 months typical for enterprise software sales
- **Pipeline Coverage**: 3-5x quota coverage ratio for healthy pipeline

### Data Quality Validation
- **Opportunity Stages**: Ensure logical stage progression without skipping stages
- **Revenue Amounts**: Positive values with reasonable magnitude for business
- **Date Consistency**: Close dates should be future or recent past, not historical
- **Currency Handling**: Proper currency codes and conversion handling

### Territory & Coverage Validation
- **Account Assignment**: Every account should have assigned owner or territory
- **Geographic Consistency**: Territory assignments should align with account geography
- **Product Specialization**: Specialized reps should focus on appropriate product lines
- **Team Coverage**: Major accounts should have appropriate team coverage
