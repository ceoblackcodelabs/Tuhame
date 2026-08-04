# blog/management/commands/seed_blog_posts.py

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from blog.models import BlogPost, CATEGORY_CHOICES

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed blog posts with SEO-optimized content for 2Hame'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌱 Seeding blog posts...'))

        # Get or create admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING('⚠️  No admin user found. Creating one...'))
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@2hame.com',
                password='admin123456'
            )
            self.stdout.write(self.style.SUCCESS('✅ Admin user created: admin / admin123456'))

        # Define blog posts with SEO content
        blog_posts = [
            {
                'title': 'The Ultimate Guide to Renting Your First Apartment in Nairobi',
                'category': 'renting-tips',
                'tags': 'Nairobi, first apartment, renting tips, tenant guide, affordable housing',
                'excerpt': 'Everything you need to know about renting your first apartment in Nairobi — from budgeting and location selection to understanding leases and avoiding common pitfalls.',
                'seo_title': 'Renting Your First Apartment in Nairobi: Complete Guide | 2Hame',
                'seo_description': 'Learn how to rent your first apartment in Nairobi with our comprehensive guide. Budgeting, location tips, lease agreements, and how 2Hame can help you find your dream home.',
                'seo_keywords': 'renting in Nairobi, first apartment, tenant tips, affordable housing Kenya, 2Hame rental guide',
                'content': '''
                    <h2>Your First Apartment in Nairobi: A Step-by-Step Guide</h2>
                    <p>Renting your first apartment is an exciting milestone — but it can also feel overwhelming. With so many neighborhoods, price ranges, and property types to choose from, where do you even start?</p>

                    <h3>Step 1: Determine Your Budget</h3>
                    <p>As a general rule, your monthly rent should not exceed <strong>30-35% of your take-home income</strong>. Don't forget to factor in:</p>
                    <ul>
                        <li><strong>Deposit:</strong> Usually 1-2 months' rent (refundable)</li>
                        <li><strong>Utilities:</strong> Water, electricity, internet, garbage collection</li>
                        <li><strong>Service Charge:</strong> Common in apartments for security, maintenance, and common areas</li>
                        <li><strong>Moving Costs:</strong> Use 2Hame's <strong>Move Cost Calculator</strong> to plan ahead</li>
                    </ul>
                    <p><em>Pro tip: 2Hame's AI search helps you find properties that match your budget with transparent pricing and no hidden fees.</em></p>

                    <h3>Step 2: Choose the Right Neighborhood</h3>
                    <p>Nairobi has a diverse range of neighborhoods — each with its own character, amenities, and price range:</p>
                    <ul>
                        <li><strong>Kilimani &amp; Kileleshwa:</strong> Popular with young professionals, lots of restaurants and nightlife</li>
                        <li><strong>Westlands:</strong> Central, vibrant, with excellent transport links</li>
                        <li><strong>Lavington &amp; Karen:</strong> More spacious, quieter, family-friendly</li>
                        <li><strong>South B &amp; South C:</strong> Affordable, growing, good transport access</li>
                        <li><strong>Eastlands:</strong> Budget-friendly, close to industrial areas</li>
                    </ul>
                    <p><strong>2Hame's interactive map</strong> shows you exactly what's available in each area, with neighborhood insights on schools, hospitals, supermarkets, and matatu stops.</p>

                    <h3>Step 3: Decide on Property Type</h3>
                    <p>What kind of home suits your lifestyle?</p>
                    <ul>
                        <li><strong>Studio or Bedsitter:</strong> Perfect for singles — compact, affordable, low-maintenance</li>
                        <li><strong>1-2 Bedroom Apartment:</strong> Great for couples, roommates, or remote workers needing a home office</li>
                        <li><strong>3+ Bedroom Apartment or Villa:</strong> Best for families, those needing more space, or group living</li>
                    </ul>

                    <h3>Step 4: Understand Your Lease Agreement</h3>
                    <p>Never sign anything without reading the fine print. Key terms to watch for:</p>
                    <ul>
                        <li><strong>Lease Duration:</strong> Usually 6-12 months — what happens if you need to leave early?</li>
                        <li><strong>Rent Increases:</strong> How much and how often can your landlord raise the rent?</li>
                        <li><strong>Maintenance Responsibility:</strong> Who fixes what? Which appliances are included?</li>
                        <li><strong>Termination Notice:</strong> How much notice must you give before moving out?</li>
                    </ul>

                    <h3>Step 5: View and Verify the Property</h3>
                    <p>Always visit the property at different times of day — what looks great at noon might be noisy at night. Check for:</p>
                    <ul>
                        <li><strong>Water pressure</strong> — especially in high-rise buildings</li>
                        <li><strong>Security</strong> — gates, guards, lighting, neighbors</li>
                        <li><strong>Connectivity</strong> — mobile network, internet availability</li>
                        <li><strong>Maintenance</strong> — common areas, cleanliness, working elevators</li>
                    </ul>
                    <p><strong>2Hame's Move Score™</strong> gives you a comprehensive property rating based on safety, transport, amenities, and cost value — so you can compare homes objectively.</p>

                    <h3>Step 6: Apply with Confidence</h3>
                    <p>Using 2Hame's <strong>digital tenant profile</strong>, you can apply to multiple properties with your verified documents — no more re-submitting the same forms over and over.</p>

                    <h3>Step 7: Plan Your Move</h3>
                    <p>Once approved, use 2Hame's <strong>Movers Marketplace</strong> to find and book verified moving companies. Compare quotes, read reviews, and arrange your move-in date — all in one place.</p>

                    <p><strong>Ready to find your first apartment?</strong> Start your search on <a href="https://2hame.com">2Hame</a> today and discover why thousands of Kenyans trust us to find their perfect home.</p>
                '''
            },
            {
                'title': 'How the 2Hame Move Score™ Works',
                'category': 'market-insights',
                'tags': 'Move Score, property scoring, housing technology, AI, smart search',
                'excerpt': 'Discover how our proprietary Move Score™ algorithm analyzes properties based on safety, transport, amenities, and value to help you find the best home in Kenya.',
                'seo_title': '2Hame Move Score™: How It Works | Property Scoring Explained',
                'seo_description': 'Learn how the 2Hame Move Score™ helps you find the best properties in Kenya by analyzing safety, transport, amenities, and cost value. Smart property scoring explained.',
                'seo_keywords': 'Move Score, property scoring, housing technology, AI search, smart property search, 2Hame',
                'content': '''
                    <h2>What is the 2Hame Move Score™?</h2>
                    <p>The <strong>2Hame Move Score™</strong> is our proprietary algorithm that helps you quickly understand the quality of a property before you even visit it. We analyze multiple data points to give every listing a score from 0-100.</p>

                    <h3>How the Score is Calculated</h3>
                    <p>Our algorithm evaluates five key dimensions:</p>

                    <h4>1. Safety Score (Weight: 25%)</h4>
                    <ul>
                        <li><strong>Neighborhood security:</strong> Crime rates, policing presence, lighting</li>
                        <li><strong>Property security:</strong> Gated access, guards, CCTV, security features</li>
                        <li><strong>Community feel:</strong> Neighbor interactions, community watch programs</li>
                    </ul>

                    <h4>2. Transport Access (Weight: 20%)</h4>
                    <ul>
                        <li>Proximity to matatu routes, bus stops, and commuter trains</li>
                        <li>Distance to major roads and highways</li>
                        <li>Availability of ride-hailing services (Uber, Bolt, Faras)</li>
                    </ul>

                    <h4>3. Nearby Amenities (Weight: 20%)</h4>
                    <ul>
                        <li><strong>Education:</strong> Schools, universities, and colleges within 2km</li>
                        <li><strong>Healthcare:</strong> Hospitals, clinics, pharmacies within 3km</li>
                        <li><strong>Shopping:</strong> Supermarkets, malls, and local markets</li>
                        <li><strong>Recreation:</strong> Parks, gyms, restaurants, and entertainment</li>
                    </ul>

                    <h4>4. Cost &amp; Value (Weight: 20%)</h4>
                    <ul>
                        <li>Property price vs. market average in the area</li>
                        <li>Value for money — what you get for your budget</li>
                        <li>Hidden costs: service charge, utilities, parking fees</li>
                    </ul>

                    <h4>5. Property Quality (Weight: 15%)</h4>
                    <ul>
                        <li>Building age and condition</li>
                        <li>Quality of finishes (floors, fixtures, kitchen)</li>
                        <li>Available amenities (gym, pool, garden, parking)</li>
                    </ul>

                    <h3>How to Use the Move Score™</h3>
                    <p>When browsing properties on 2Hame, look for the <strong>gold badge</strong> with the score. Here's what the scores mean:</p>
                    <ul>
                        <li><strong>90+ — Excellent Move</strong> ✨: Top-tier properties in the best locations</li>
                        <li><strong>80-89 — Great Choice</strong> 🌟: High-quality homes with good amenities</li>
                        <li><strong>70-79 — Solid Option</strong> 👍: Good value with some trade-offs</li>
                        <li><strong>60-69 — Consider Carefully</strong> 🤔: Decent but may have drawbacks</li>
                        <li><strong>Below 60 — Proceed with Caution</strong> ⚠️: Significant compromises</li>
                    </ul>

                    <h3>Why Trust the Move Score™?</h3>
                    <p>Our algorithm is continuously refined using real tenant feedback, property performance data, and local insights from our team on the ground in Kenya. We combine objective data with human expertise to deliver a score you can trust.</p>

                    <p><strong>Ready to find your next home?</strong> Browse properties on 2Hame and let the Move Score™ guide you to the perfect match.</p>
                '''
            },
            {
                'title': 'Top 10 Tips for First-Time Landlords in Kenya',
                'category': 'landlord-guides',
                'tags': 'landlord tips, rental property, property management, tenant screening, Kenya',
                'excerpt': 'New to being a landlord? From tenant screening and lease agreements to property maintenance — our top 10 tips will help you succeed in the Kenyan rental market.',
                'seo_title': '10 Essential Tips for First-Time Landlords in Kenya | 2Hame Guide',
                'seo_description': 'Discover 10 essential tips for first-time landlords in Kenya. Learn tenant screening, lease agreements, property maintenance, and how 2Hame helps you find great tenants.',
                'seo_keywords': 'landlord tips, rental property management, tenant screening Kenya, property investment, 2Hame landlord guide',
                'content': '''
                    <h2>10 Tips for First-Time Landlords in Kenya</h2>
                    <p>Becoming a landlord can be a rewarding investment — but it comes with responsibilities. Here are our top 10 tips to help you succeed.</p>

                    <h3>1. Know the Legal Requirements</h3>
                    <p>Understand your obligations under the Kenyan <strong>Landlord and Tenant Act</strong>. You must:</p>
                    <ul>
                        <li>Register your rental income with KRA and pay taxes</li>
                        <li>Provide a written lease agreement that complies with Kenyan law</li>
                        <li>Ensure your property meets health and safety standards</li>
                        <li>Protect tenant deposits (maximum 1 month's rent)</li>
                    </ul>

                    <h3>2. Screen Tenants Thoroughly</h3>
                    <p>Finding the right tenant is crucial. Use 2Hame's <strong>digital tenant profiles</strong> to see:</p>
                    <ul>
                        <li>Previous rental history and references</li>
                        <li>Employment verification and income verification</li>
                        <li>Credit checks and payment reliability</li>
                        <li>Identification and KYC documents</li>
                    </ul>

                    <h3>3. Set Competitive Rent</h3>
                    <p>Research the market in your area. List your property on 2Hame and use our <strong>owner dashboard</strong> to see:</p>
                    <ul>
                        <li>Average rents for similar properties in your neighborhood</li>
                        <li>Demand patterns and seasonal trends</li>
                        <li>How your property compares to active listings</li>
                    </ul>

                    <h3>4. Write a Solid Lease Agreement</h3>
                    <p>A clear, written lease protects both you and the tenant. Include:</p>
                    <ul>
                        <li>Rent amount, due date, and late payment penalties</li>
                        <li>Term of lease (start and end dates)</li>
                        <li>Rules for pets, smoking, and guests</li>
                        <li>Maintenance responsibilities for both parties</li>
                        <li>Termination and notice requirements</li>
                    </ul>

                    <h3>5. Maintain Your Property</h3>
                    <p>A well-maintained property attracts better tenants and commands higher rent. Stay on top of:</p>
                    <ul>
                        <li>Plumbing, electrical, and roofing maintenance</li>
                        <li>Clean common areas and landscaping</li>
                        <li>Working security features (gates, alarms, lighting)</li>
                        <li>Prompt repairs — responding quickly to issues</li>
                    </ul>

                    <h3>6. Handle Deposits Legally</h3>
                    <p>In Kenya, you can collect a refundable deposit of up to <strong>1 month's rent</strong>. Always provide a written receipt and a clear record of deductions when tenants move out.</p>

                    <h3>7. Build Good Tenant Relationships</h3>
                    <p>Happy tenants stay longer and take better care of your property. Build trust by:</p>
                    <ul>
                        <li>Responding quickly to messages and issues</li>
                        <li>Being fair and transparent in all dealings</li>
                        <li>Respecting tenant privacy and quiet enjoyment</li>
                        <li>Using 2Hame's <strong>direct communication</strong> for secure, documented conversations</li>
                    </ul>

                    <h3>8. Know When to Increase Rent</h3>
                    <p>In Kenya, you can increase rent once every 12 months with proper notice (usually 1-2 months). Base your increase on:</p>
                    <ul>
                        <li>Market rates for similar properties</li>
                        <li>Inflation and cost of living</li>
                        <li>Improvements you've made to the property</li>
                    </ul>

                    <h3>9. Use 2Hame for Listing &amp; Management</h3>
                    <p>List your property for free on 2Hame and get:</p>
                    <ul>
                        <li><strong>Real-time analytics</strong> — track views, saves, and inquiries</li>
                        <li><strong>Premium visibility options</strong> to attract more tenants</li>
                        <li><strong>Secure payment processing</strong> for rent and deposits</li>
                        <li><strong>Verified tenant profiles</strong> with documents and history</li>
                    </ul>

                    <h3>10. Have an Eviction Plan (But Hope You Never Need It)</h3>
                    <p>While no one likes to think about it, you need to understand the legal eviction process in Kenya. Always follow the law:</p>
                    <ul>
                        <li>Provide proper written notice for non-payment or breach</li>
                        <li>File in court if necessary — never take matters into your own hands</li>
                        <li>Document everything — 2Hame's communication logs can help</li>
                    </ul>

                    <p><strong>Ready to list your property?</strong> Create your free listing on <a href="https://2hame.com">2Hame</a> today and reach thousands of verified tenants in Kenya.</p>
                '''
            },
            {
                'title': 'How to Use the 2Hame Movers Marketplace',
                'category': 'moving-guides',
                'tags': 'movers Kenya, moving services, relocation, logistics, moving tips',
                'excerpt': 'Learn how 2Hame\'s Movers Marketplace helps you find, compare, and book verified moving companies in Kenya for a stress-free relocation experience.',
                'seo_title': '2Hame Movers Marketplace: Find Verified Movers in Kenya | Moving Guide',
                'seo_description': 'Find and book verified moving companies in Kenya with 2Hame\'s Movers Marketplace. Compare quotes, read reviews, and plan your stress-free move.',
                'seo_keywords': 'movers Kenya, moving services, relocation guide, verified movers, 2Hame movers marketplace',
                'content': '''
                    <h2>Your Stress-Free Move Starts Here</h2>
                    <p>Moving to a new home can be one of life's most stressful experiences — but with 2Hame's <strong>Movers Marketplace</strong>, it doesn't have to be. We've created a one-stop platform to find, compare, and book verified moving companies across Kenya.</p>

                    <h3>Why Use the Movers Marketplace?</h3>
                    <h4>✅ Verified Moving Companies Only</h4>
                    <p>Every mover on our platform is verified — we check their licenses, insurance, and customer reviews before they can list their services.</p>

                    <h4>🤝 Compare Quotes in Minutes</h4>
                    <p>Get quotes from multiple moving companies and compare prices, services, and availability side by side. No more endless phone calls or email threads.</p>

                    <h4>⭐ Real Customer Reviews</h4>
                    <p>Read honest reviews from people who have used these movers. We don't edit or delete reviews — you see the good and the bad.</p>

                    <h4>💰 Transparent Pricing</h4>
                    <p>No hidden fees. Movers provide clear, itemized quotes so you know exactly what you're paying for — including packing, loading, transport, and unloading.</p>

                    <h3>How to Use the Movers Marketplace</h3>

                    <h4>Step 1: Tell Us About Your Move</h4>
                    <ul>
                        <li>Current and new address</li>
                        <li>Property size (apartment, house, villa)</li>
                        <li>How much stuff you have (studio, 1-2 bedrooms, 3+ bedrooms)</li>
                        <li>Packing help needed? (yes/no)</li>
                        <li>Move date and timeline</li>
                    </ul>

                    <h4>Step 2: Get Matched with Movers</h4>
                    <p>Our algorithm matches you with moving companies that fit your needs. You'll get up to <strong>3-5 recommended movers</strong> with their profiles, reviews, and estimated quotes.</p>

                    <h4>Step 3: Compare and Choose</h4>
                    <ul>
                        <li>Review quotes and packages</li>
                        <li>Read customer testimonials</li>
                        <li>Check availability on your chosen dates</li>
                        <li>Communicate directly via our <strong>secure chat</strong></li>
                    </ul>

                    <h4>Step 4: Book and Move</h4>
                    <p>Confirm your booking, schedule your moving day, and get tracking updates. Use 2Hame's <strong>Move Cost Calculator</strong> to plan your budget — and move with confidence.</p>

                    <h3>More Than Just Moving</h3>
                    <p>The Movers Marketplace connects you with:</p>
                    <ul>
                        <li><strong>Local Movers</strong> — For moves within the same city or town</li>
                        <li><strong>Long-Distance Movers</strong> — Across Kenya, between cities and counties</li>
                        <li><strong>Corporate Movers</strong> — Office and business relocations</li>
                        <li><strong>Storage Solutions</strong> — Short and long-term storage for your belongings</li>
                    </ul>

                    <p><strong>Ready to move?</strong> Visit <a href="https://2hame.com/movers">2Hame's Movers Marketplace</a> and find your perfect moving partner today.</p>
                '''
            },
            {
                'title': 'Neighborhood Spotlight: Living in Kilimani, Nairobi',
                'category': 'neighborhood-guides',
                'tags': 'Kilimani Nairobi, neighborhood guide, housing areas, living in Nairobi',
                'excerpt': 'A detailed guide to Kilimani — one of Nairobi\'s most popular neighborhoods for young professionals, with excellent amenities, transport links, and a vibrant community.',
                'seo_title': 'Kilimani Neighborhood Guide: Living in Nairobi\'s Trendiest Area | 2Hame',
                'seo_description': 'Discover why Kilimani is one of Nairobi\'s most sought-after neighborhoods. Schools, hospitals, transport, and housing options — all in one guide.',
                'seo_keywords': 'Kilimani Nairobi, neighborhood guide, living in Kilimani, housing in Nairobi, 2Hame neighborhood insights',
                'content': '''
                    <h2>Welcome to Kilimani</h2>
                    <p>Kilimani has become one of Nairobi's most desirable neighborhoods — and it's easy to see why. With its central location, vibrant nightlife, and excellent amenities, it's the go-to choice for young professionals, expats, and families alike.</p>

                    <h3>Why Kilimani?</h3>

                    <h4>📍 Prime Location</h4>
                    <p>Situated between the city center and the upscale suburbs of Karen and Lang'ata, Kilimani offers the best of both worlds:</p>
                    <ul>
                        <li><strong>10 minutes</strong> from the CBD</li>
                        <li><strong>15 minutes</strong> from Wilson Airport</li>
                        <li><strong>20 minutes</strong> from the Southern Bypass</li>
                        <li><strong>5 minutes</strong> from Westlands</li>
                    </ul>

                    <h4>🛍️ Shopping &amp; Dining</h4>
                    <ul>
                        <li><strong>Yaya Centre</strong> — One of Nairobi's oldest and most popular malls</li>
                        <li><strong>The Alchemist</strong> — Trendy bar and food market</li>
                        <li><strong>Prestige Plaza</strong> — Shopping, banking, and dining</li>
                        <li>Countless restaurants, coffee shops, and local eateries</li>
                    </ul>

                    <h4>🏥 Healthcare</h4>
                    <ul>
                        <li><strong>Nairobi Hospital</strong> — Kenya's leading private hospital (5 mins)</li>
                        <li><strong>Aga Khan Hospital</strong> — World-class medical care (10 mins)</li>
                        <li>Numerous clinics and pharmacies within walking distance</li>
                    </ul>

                    <h4>🏫 Education</h4>
                    <ul>
                        <li><strong>Kilimani Primary School</strong> — Public school with excellent reputation</li>
                        <li><strong>Braeburn School</strong> — International curriculum options</li>
                        <li><strong>St. Mary's School</strong> — Top private school in Nairobi</li>
                        <li>Multiple pre-schools and daycare centers</li>
                    </ul>

                    <h4>🚌 Transport</h4>
                    <ul>
                        <li>Excellent matatu routes to CBD, Westlands, and surrounding areas</li>
                        <li>Dedicated Uber/Bolt zones for quick pickups</li>
                        <li>Good road network, though peak hours can be congested</li>
                    </ul>

                    <h3>Housing in Kilimani</h3>
                    <p>Kilimani offers diverse housing options — from budget-friendly studio apartments to luxury penthouses:</p>
                    <ul>
                        <li><strong>Studios: </strong>KES 15,000 - 30,000/month</li>
                        <li><strong>1-Bedroom: </strong>KES 25,000 - 60,000/month</li>
                        <li><strong>2-Bedroom: </strong>KES 45,000 - 120,000/month</li>
                        <li><strong>3-Bedroom: </strong>KES 80,000 - 200,000/month</li>
                        <li><strong>Luxury Villas: </strong>KES 150,000+/month</li>
                    </ul>

                    <h3>Kilimani Move Score™</h3>
                    <div style="background:#f0f9ff;padding:1rem;border-radius:8px;">
                        <p><strong>Overall Move Score: 89/100 — Great Choice!</strong></p>
                        <ul>
                            <li>🏅 Safety: 85/100</li>
                            <li>🚌 Transport: 92/100</li>
                            <li>🏪 Amenities: 94/100</li>
                            <li>💰 Cost &amp; Value: 86/100</li>
                            <li>🏠 Property Quality: 88/100</li>
                        </ul>
                    </div>

                    <h3>What Locals Say</h3>
                    <p><em>"I've lived in Kilimani for 5 years and love the convenience. Everything I need is within walking distance — and there's always something happening. It feels like a community."</em></p>

                    <p><strong>Find your home in Kilimani</strong> — browse available properties on <a href="https://2hame.com">2Hame</a> and discover why it's one of Nairobi's most loved neighborhoods.</p>
                '''
            },
            {
                'title': 'Why 2Hame is Kenya\'s Smartest Housing Platform',
                'category': 'company-news',
                'tags': '2Hame, housing platform, real estate technology, property marketplace, Kenya',
                'excerpt': 'Discover how 2Hame is transforming the Kenyan real estate market with AI-powered search, verified listings, and innovative features like the Move Score™.',
                'seo_title': '2Hame: Kenya\'s Smartest Housing Platform | Real Estate Technology',
                'seo_description': 'Learn how 2Hame is revolutionizing real estate in Kenya with AI search, Move Score™, verified listings, and tools for tenants and property owners.',
                'seo_keywords': '2Hame, housing platform, real estate Kenya, property marketplace, real estate technology, smart housing',
                'content': '''
                    <h2>From Finding to Moving — 2Hame Does It All</h2>
                    <p>2Hame isn't just another property listing site. We're a complete ecosystem designed to make finding, listing, and moving into your perfect home as seamless as possible. Here's why thousands of Kenyans trust us.</p>

                    <h3>For Home Seekers: More Than Just Listings</h3>
                    <ul>
                        <li><strong>AI-Powered Search</strong> — Find exactly what you're looking for with intelligent filters that understand neighborhoods, commute times, and lifestyle preferences.</li>
                        <li><strong>Interactive Map</strong> — See properties on a live map with school zones, transport links, and amenity overlays.</li>
                        <li><strong>2Hame Move Score™</strong> — A proprietary algorithm that rates properties on safety, transport, amenities, and value — so you can compare homes objectively.</li>
                        <li><strong>Digital Tenant Profile</strong> — Build a verified profile with documents, rental history, and references to apply faster.</li>
                        <li><strong>Direct Communication</strong> — Talk directly to landlords, agents, and movers with secure, encrypted messaging.</li>
                        <li><strong>Move Cost Calculator</strong> — Plan your entire budget — from rent and deposits to moving services and utility setup.</li>
                    </ul>

                    <h3>For Property Owners: Tools That Work</h3>
                    <ul>
                        <li><strong>Free Listings</strong> — List your property at no cost, with premium visibility options available.</li>
                        <li><strong>Analytics Dashboard</strong> — Track views, saves, inquiries, and performance metrics in real-time.</li>
                        <li><strong>Verified Tenant Profiles</strong> — Access verified documents, rental history, and references before approving applicants.</li>
                        <li><strong>Secure Payments</strong> — Process deposits and rent securely with multiple payment options.</li>
                        <li><strong>Direct Communication</strong> — Connect directly with serious tenants and buyers — no middlemen.</li>
                    </ul>

                    <h3>For Movers: A Marketplace That Works</h3>
                    <ul>
                        <li><strong>Verified Listing</strong> — Get listed as a verified mover with reviews and ratings.</li>
                        <li><strong>Direct Client Connection</strong> — Tenants and owners can contact you directly for quotes.</li>
                        <li><strong>Lead Generation</strong> — Receive qualified leads from people actively planning their move.</li>
                        <li><strong>Track Record</strong> — Build your reputation through real customer reviews.</li>
                    </ul>

                    <h3>Why 2Hame is Different</h3>
                    <ul>
                        <li><strong>🏆 Built for Kenya</strong> — Local pricing, local neighborhoods, local support. Designed for Kenyans by Kenyans.</li>
                        <li><strong>🔒 Secure &amp; Trusted</strong> — End-to-end encryption, verified listings, and secure payments.</li>
                        <li><strong>💡 Innovative Technology</strong> — AI search, Move Score™, interactive maps — we're redefining how Kenyans find homes.</li>
                        <li><strong>🤝 Community-Driven</strong> — Real reviews, honest feedback, and a platform built on trust.</li>
                    </ul>

                    <h3>Join the 2Hame Community</h3>
                    <ul>
                        <li><strong>12,500+</strong> active property listings</li>
                        <li><strong>8,200+</strong> happy tenants</li>
                        <li><strong>2,300+</strong> property owners and landlords</li>
                        <li><strong>47</strong> cities and towns across Kenya</li>
                        <li><strong>24/7</strong> customer support</li>
                    </ul>

                    <p><strong>Ready to experience the future of housing in Kenya?</strong> Visit <a href="https://2hame.com">2Hame.com</a> today and find, list, or move — all in one place.</p>
                '''
            }
        ]

        # Create blog posts
        created_count = 0
        for post_data in blog_posts:
            # Check if post already exists by title
            if BlogPost.objects.filter(title=post_data['title']).exists():
                self.stdout.write(self.style.WARNING(f"⏭️  Skipping '{post_data['title']}' — already exists"))
                continue

            # Create the post
            post = BlogPost.objects.create(
                title=post_data['title'],
                author=admin_user,
                category=post_data['category'],
                tags=post_data['tags'],
                excerpt=post_data['excerpt'],
                seo_title=post_data['seo_title'],
                seo_description=post_data['seo_description'],
                seo_keywords=post_data['seo_keywords'],
                content=post_data['content'],
                published_at=timezone.now() - timedelta(days=random.randint(1, 90)),
                is_published=True,
                views_count=random.randint(100, 5000)
            )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"✅ Created: '{post.title}'"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Successfully seeded {created_count} blog posts!"))
        self.stdout.write(self.style.SUCCESS("\n📊 Summary:"))
        self.stdout.write(f"   Total posts in database: {BlogPost.objects.count()}")
        self.stdout.write(f"   Published posts: {BlogPost.objects.filter(is_published=True).count()}")
        self.stdout.write(f"   Categories: {BlogPost.objects.values('category').distinct().count()}")

        # Show category breakdown
        self.stdout.write(self.style.SUCCESS("\n📂 Category Breakdown:"))
        for category_code, category_label in CATEGORY_CHOICES:
            count = BlogPost.objects.filter(category=category_code).count()
            if count > 0:
                self.stdout.write(f"   - {category_label}: {count} posts")