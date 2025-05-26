import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
import json
from urllib.parse import urljoin, urlparse
import openai
from typing import Dict, List, Optional
import plotly.express as px
import plotly.graph_objects as go

# Configure page
st.set_page_config(
    page_title="Succession Signal",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f4e79;
    }
    .high-score { border-left-color: #dc3545; }
    .medium-score { border-left-color: #ffc107; }
    .low-score { border-left-color: #28a745; }
</style>
""", unsafe_allow_html=True)

class SuccessionSignal:
    def __init__(self):
        self.openai_api_key = None
        
    def set_openai_key(self, api_key: str):
        """Set OpenAI API key"""
        self.openai_api_key = api_key
        openai.api_key = api_key
    
    def scrape_website_data(self, url: str) -> Dict:
        """Scrape basic website data to assess digital activity"""
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic info
            title = soup.find('title')
            title_text = title.text.strip() if title else ""
            
            # Look for copyright dates
            copyright_years = []
            text_content = soup.get_text().lower()
            copyright_matches = re.findall(r'copyright.*?(\d{4})', text_content)
            copyright_matches.extend(re.findall(r'©.*?(\d{4})', text_content))
            
            if copyright_matches:
                copyright_years = [int(year) for year in copyright_matches if 1990 <= int(year) <= 2024]
            
            # Check for blog/news sections
            has_blog = bool(soup.find(['a', 'link'], href=re.compile(r'blog|news', re.I)))
            
            # Check for careers/hiring pages
            has_careers = bool(soup.find(['a', 'link'], href=re.compile(r'career|job|hiring', re.I)))
            
            # Look for last updated dates
            last_updated = None
            date_patterns = [
                r'last updated:?\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'updated:?\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text_content, re.I)
                if matches:
                    try:
                        last_updated = datetime.strptime(matches[0], '%m/%d/%Y')
                        break
                    except:
                        continue
            
            return {
                'accessible': True,
                'title': title_text,
                'copyright_years': copyright_years,
                'latest_copyright': max(copyright_years) if copyright_years else None,
                'has_blog': has_blog,
                'has_careers': has_careers,
                'last_updated': last_updated,
                'text_length': len(text_content)
            }
            
        except Exception as e:
            return {
                'accessible': False,
                'error': str(e),
                'title': '',
                'copyright_years': [],
                'latest_copyright': None,
                'has_blog': False,
                'has_careers': False,
                'last_updated': None,
                'text_length': 0
            }
    
    def calculate_succession_score(self, business_data: Dict) -> Dict:
        """Calculate succession readiness score based on various factors"""
        score = 0
        factors = []
        
        current_year = datetime.now().year
        
        # Age of business (higher score for older businesses)
        if business_data.get('founded_year'):
            age = current_year - business_data['founded_year']
            if age >= 20:
                score += 25
                factors.append(f"Established business ({age} years)")
            elif age >= 10:
                score += 15
                factors.append(f"Mature business ({age} years)")
        
        # Website analysis
        website_data = business_data.get('website_data', {})
        
        if not website_data.get('accessible'):
            score += 20
            factors.append("Website inaccessible/outdated")
        else:
            # Old copyright dates
            latest_copyright = website_data.get('latest_copyright')
            if latest_copyright and current_year - latest_copyright >= 3:
                score += 15
                factors.append(f"Copyright last updated {latest_copyright}")
            
            # No recent blog/news activity
            if not website_data.get('has_blog'):
                score += 10
                factors.append("No blog/news section")
            
            # No careers page
            if not website_data.get('has_careers'):
                score += 10
                factors.append("No careers/hiring page")
        
        # Industry factors (some industries have higher succession rates)
        high_succession_industries = [
            'construction', 'manufacturing', 'automotive', 'plumbing', 
            'electrical', 'hvac', 'roofing', 'landscaping', 'trucking'
        ]
        
        industry = business_data.get('industry', '').lower()
        for high_industry in high_succession_industries:
            if high_industry in industry:
                score += 15
                factors.append(f"High-succession industry ({industry})")
                break
        
        # Revenue range (sweet spot for succession)
        revenue = business_data.get('estimated_revenue', 0)
        if 2000000 <= revenue <= 10000000:
            score += 20
            factors.append("Target revenue range ($2M-$10M)")
        
        # Location factors (smaller markets often have higher succession needs)
        location = business_data.get('location', '').lower()
        if any(state in location for state in ['va', 'virginia', 'co', 'colorado', 'tn', 'tennessee']):
            score += 10
            factors.append("Target geographic region")
        
        # Normalize score to 0-100
        max_possible_score = 115
        normalized_score = min(100, (score / max_possible_score) * 100)
        
        # Categorize score
        if normalized_score >= 70:
            category = "High"
            priority = "🔴"
        elif normalized_score >= 40:
            category = "Medium"
            priority = "🟡"
        else:
            category = "Low"
            priority = "🟢"
        
        return {
            'score': round(normalized_score, 1),
            'category': category,
            'priority': priority,
            'factors': factors,
            'raw_score': score
        }
    
    def generate_ai_summary(self, business_data: Dict, succession_data: Dict) -> str:
        """Generate AI-powered outreach summary"""
        if not self.openai_api_key:
            return "AI summary requires OpenAI API key"
        
        try:
            prompt = f"""
            Create a warm, professional 2-3 sentence summary for a business acquisition outreach. Focus on succession readiness signals.

            Business: {business_data.get('name', 'Unknown')}
            Industry: {business_data.get('industry', 'Unknown')}
            Location: {business_data.get('location', 'Unknown')}
            Founded: {business_data.get('founded_year', 'Unknown')}
            Succession Score: {succession_data['score']}/100
            Key Factors: {', '.join(succession_data['factors'][:3])}

            Write this as if you're briefing a business development professional who will make a respectful call about succession planning. Be specific about the signals but keep it conversational and warm.

            Example tone: "John runs ABC Plumbing in Denver, CO. The company has been operating for 25 years, but their website hasn't been updated since 2019 and they're not actively hiring. This suggests potential succession timing - worth a respectful conversation about future planning."
            """
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"AI summary unavailable: {str(e)}"

def load_sample_data():
    """Load sample business data for demo"""
    sample_businesses = [
        {
            'name': 'Richmond Environmental Solutions',
            'industry': 'Environmental Remediation',
            'location': 'Richmond, VA',
            'website': 'richmondenviro.com',
            'founded_year': 1998,
            'estimated_revenue': 4500000,
            'employees': 25
        },
        {
            'name': 'Blue Ridge HVAC Services',
            'industry': 'HVAC Contracting',
            'location': 'Charlottesville, VA',
            'website': 'blueridgehvac.net',
            'founded_year': 1995,
            'estimated_revenue': 3200000,
            'employees': 18
        },
        {
            'name': 'Denver Data Recovery Inc',
            'industry': 'IT Services',
            'location': 'Denver, CO',
            'website': 'denverdatarecovery.com',
            'founded_year': 2001,
            'estimated_revenue': 2800000,
            'employees': 12
        },
        {
            'name': 'Tennessee Trucking Co',
            'industry': 'Transportation & Logistics',
            'location': 'Nashville, TN',
            'website': 'tntrucking.com',
            'founded_year': 1989,
            'estimated_revenue': 8500000,
            'employees': 45
        },
        {
            'name': 'Apex Construction Group',
            'industry': 'General Contracting',
            'location': 'Colorado Springs, CO',
            'website': 'apexconstruct.biz',
            'founded_year': 1992,
            'estimated_revenue': 6200000,
            'employees': 32
        }
    ]
    
    return sample_businesses

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Succession Signal</h1>
        <p>AI-Powered Acquisition Signal Engine for Legacy Holdings</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize the app
    succession_app = SuccessionSignal()
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    
    # OpenAI API Key input
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", 
                                   help="Required for AI-generated summaries")
    if api_key:
        succession_app.set_openai_key(api_key)
    
    # Region filter
    regions = st.sidebar.multiselect(
        "Target Regions",
        ["Virginia", "Colorado", "Tennessee", "North Carolina", "Alabama"],
        default=["Virginia", "Colorado", "Tennessee"]
    )
    
    # Score threshold
    min_score = st.sidebar.slider("Minimum Succession Score", 0, 100, 40)
    
    # Load sample data
    if 'business_data' not in st.session_state:
        st.session_state.business_data = load_sample_data()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Deal Pipeline", "📊 Analytics", "⚙️ Data Management"])
    
    with tab1:
        st.header("High-Priority Succession Targets")
        
        # Process each business
        processed_businesses = []
        
        for business in st.session_state.business_data:
            # Filter by region
            business_region = business['location'].split(',')[-1].strip()
            region_match = any(region.lower() in business_region.lower() for region in regions)
            
            if not region_match:
                continue
            
            # Scrape website data (in demo, we'll simulate this)
            website_data = {
                'accessible': True,
                'latest_copyright': 2019 if 'enviro' in business['name'].lower() else 2021,
                'has_blog': False,
                'has_careers': False
            }
            business['website_data'] = website_data
            
            # Calculate succession score
            succession_data = succession_app.calculate_succession_score(business)
            
            # Filter by minimum score
            if succession_data['score'] < min_score:
                continue
            
            # Generate AI summary
            ai_summary = succession_app.generate_ai_summary(business, succession_data)
            
            processed_businesses.append({
                **business,
                'succession_score': succession_data['score'],
                'succession_category': succession_data['category'],
                'succession_factors': succession_data['factors'],
                'ai_summary': ai_summary,
                'priority': succession_data['priority']
            })
        
        # Sort by succession score
        processed_businesses.sort(key=lambda x: x['succession_score'], reverse=True)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Targets", len(processed_businesses))
        with col2:
            high_priority = len([b for b in processed_businesses if b['succession_score'] >= 70])
            st.metric("High Priority", high_priority)
        with col3:
            avg_score = sum(b['succession_score'] for b in processed_businesses) / len(processed_businesses) if processed_businesses else 0
            st.metric("Avg Score", f"{avg_score:.1f}")
        with col4:
            total_revenue = sum(b['estimated_revenue'] for b in processed_businesses)
            st.metric("Pipeline Value", f"${total_revenue/1000000:.1f}M")
        
        # Display business cards
        for business in processed_businesses:
            with st.expander(f"{business['priority']} {business['name']} - Score: {business['succession_score']}", expanded=business['succession_score'] >= 70):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Industry:** {business['industry']}")
                    st.write(f"**Location:** {business['location']}")
                    st.write(f"**Founded:** {business['founded_year']} ({datetime.now().year - business['founded_year']} years)")
                    st.write(f"**Est. Revenue:** ${business['estimated_revenue']:,}")
                    
                    st.write("**AI Summary:**")
                    st.info(business['ai_summary'])
                    
                    st.write("**Succession Signals:**")
                    for factor in business['succession_factors']:
                        st.write(f"• {factor}")
                
                with col2:
                    # Score gauge
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = business['succession_score'],
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        title = {'text': "Succession Score"},
                        gauge = {
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "darkblue"},
                            'steps': [
                                {'range': [0, 40], 'color': "lightgreen"},
                                {'range': [40, 70], 'color': "yellow"},
                                {'range': [70, 100], 'color': "red"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 70
                            }
                        }
                    ))
                    fig.update_layout(height=200)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"Export to CRM", key=f"export_{business['name']}"):
                        st.success("Exported to CRM!")
                with col2:
                    if st.button(f"Schedule Outreach", key=f"schedule_{business['name']}"):
                        st.success("Added to outreach calendar!")
                with col3:
                    if st.button(f"Research Deep Dive", key=f"research_{business['name']}"):
                        st.info("Research task created!")
    
    with tab2:
        st.header("Pipeline Analytics")
        
        if processed_businesses:
            # Score distribution
            scores = [b['succession_score'] for b in processed_businesses]
            fig1 = px.histogram(x=scores, nbins=10, title="Succession Score Distribution")
            fig1.update_xaxis(title="Succession Score")
            fig1.update_yaxis(title="Number of Businesses")
            st.plotly_chart(fig1, use_container_width=True)
            
            # Industry breakdown
            industries = {}
            for b in processed_businesses:
                industry = b['industry']
                if industry not in industries:
                    industries[industry] = 0
                industries[industry] += 1
            
            fig2 = px.pie(values=list(industries.values()), names=list(industries.keys()), 
                         title="Target Industries")
            st.plotly_chart(fig2, use_container_width=True)
            
            # Regional distribution
            regions_data = {}
            for b in processed_businesses:
                region = b['location'].split(',')[-1].strip()
                if region not in regions_data:
                    regions_data[region] = []
                regions_data[region].append(b['succession_score'])
            
            if regions_data:
                region_names = list(regions_data.keys())
                avg_scores = [sum(scores)/len(scores) for scores in regions_data.values()]
                
                fig3 = px.bar(x=region_names, y=avg_scores, title="Average Succession Score by Region")
                fig3.update_xaxis(title="Region")
                fig3.update_yaxis(title="Average Score")
                st.plotly_chart(fig3, use_container_width=True)
    
    with tab3:
        st.header("Data Management")
        
        st.subheader("Upload Business Data")
        uploaded_file = st.file_uploader("Upload CSV with business data", type=['csv'])
        
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.write("Preview:")
            st.dataframe(df.head())
            
            if st.button("Process Uploaded Data"):
                # Convert DataFrame to business list
                new_businesses = df.to_dict('records')
                st.session_state.business_data.extend(new_businesses)
                st.success(f"Added {len(new_businesses)} businesses to the database!")
        
        st.subheader("Current Database")
        if st.session_state.business_data:
            df = pd.DataFrame(st.session_state.business_data)
            st.dataframe(df)
            
            # Export functionality
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="succession_targets.csv",
                mime="text/csv"
            )
        
        # Manual business entry
        st.subheader("Add Business Manually")
        with st.form("add_business"):
            name = st.text_input("Business Name")
            industry = st.text_input("Industry")
            location = st.text_input("Location")
            website = st.text_input("Website")
            founded_year = st.number_input("Founded Year", min_value=1900, max_value=2024, value=2000)
            revenue = st.number_input("Estimated Revenue", min_value=0, value=1000000)
            employees = st.number_input("Employees", min_value=1, value=10)
            
            if st.form_submit_button("Add Business"):
                new_business = {
                    'name': name,
                    'industry': industry,
                    'location': location,
                    'website': website,
                    'founded_year': founded_year,
                    'estimated_revenue': revenue,
                    'employees': employees
                }
                st.session_state.business_data.append(new_business)
                st.success(f"Added {name} to the database!")

if __name__ == "__main__":
    main()
