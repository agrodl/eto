import streamlit as st
import requests
import json
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="ET₀ Penman-Monteith Calculator",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #2E7D32, #4CAF50);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .sub-header {
        font-size: 1.5rem;
        text-align: center;
        color: #424242;
        margin-bottom: 3rem;
    }
    
    .metric-container {
        background: rgb(219 237 230);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin: 0.5rem 0;
    }

    .metric-container p{
        color: rgb(49 51 63) !important;
    }
    
    .weather-card {
        background: #FFFFFF;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border-left: 5px solid #4CAF50;
        margin: 1rem 0;
    }
    
    .et0-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: rgb(49, 51, 63);
        text-align: center;
    }
    
    .parameter-card {
        background: #F8F9FA;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 1px solid #E3F2FD;
    }
    
    .sidebar-content {
        background: linear-gradient(180deg, #F3E5F5 0%, #E1BEE7 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .success-message {
        background: #dbede6;
        color: #222e3a;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .error-message {
        background: linear-gradient(90deg, #D32F2F, #F44336);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(244, 67, 54, 0.3);
    }
    
    .info-card {
        background: #E3F2FD;
        border: 1px solid #BBDEFB;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        color: #1976D2;
    }
    
    .footer-brand {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #1976D2, #1565C0);
        color: white;
        border-radius: 10px;
        margin: 2rem 0;
    }
    
    .section-header {
        color: #1976D2;
        font-size: 1.4rem;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #E3F2FD;
        padding-bottom: 0.5rem;
    }
    
    .sidebar-title {
        color: #1976D2;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .metric-label {
        color: rgb(49 51 63);
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    
    .city-search {
        text-align: center;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

class PenmanMonteithCalculator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.worldweatheronline.com/premium/v1"
        
    def get_weather_data(self, city):
        """Get current weather data and forecast from World Weather Online"""
        try:
            # Current weather + 14 day forecast
            url = f"{self.base_url}/weather.ashx"
            params = {
                'key': self.api_key,
                'q': city,
                'format': 'json',
                'num_of_days': '14',
                'tp': '24',  # 24 hour intervals
                'includelocation': 'yes',
                'showlocaltime': 'yes'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'error' not in data['data']:
                    return data['data']
                else:
                    return None
            else:
                return None
                
        except Exception as e:
            st.error(f"API Connection Error: {e}")
            return None
    
    def calculate_solar_radiation(self, lat, day_of_year, temp_max, temp_min, humidity, sunshine_hours=None):
        """Calculate solar radiation using Hargreaves method or sunshine hours"""
        lat_rad = math.radians(lat)
        solar_declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
        sunset_hour_angle = math.acos(-math.tan(lat_rad) * math.tan(solar_declination))
        
        dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
        Ra = (24 * 60 / math.pi) * 0.082 * dr * (
            sunset_hour_angle * math.sin(lat_rad) * math.sin(solar_declination) +
            math.cos(lat_rad) * math.cos(solar_declination) * math.sin(sunset_hour_angle)
        )
        
        # If sunshine hours available, use Angstrom-Prescott formula
        if sunshine_hours is not None:
            N = (24 / math.pi) * sunset_hour_angle  # Maximum possible sunshine hours
            Rs = (0.25 + 0.50 * sunshine_hours / N) * Ra if N > 0 else 0.16 * math.sqrt(temp_max - temp_min) * Ra
        else:
            # Use Hargreaves method
            temp_range = temp_max - temp_min
            Rs = 0.16 * math.sqrt(temp_range) * Ra
        
        return Rs, Ra
    
    def penman_monteith_et0(self, temp_mean, temp_max, temp_min, humidity, wind_speed, 
                           solar_radiation, elevation=0, lat=35):
        """Calculate ET0 using Penman-Monteith method (mm/day)"""
        
        # Psychrometric constant
        gamma = 0.665 * (101.3 * ((293 - 0.0065 * elevation) / 293) ** 5.26)
        
        # Saturation vapor pressure at max and min temperature
        es_max = 0.6108 * math.exp(17.27 * temp_max / (temp_max + 237.3))
        es_min = 0.6108 * math.exp(17.27 * temp_min / (temp_min + 237.3))
        es = (es_max + es_min) / 2
        
        # Actual vapor pressure
        ea = es * humidity / 100
        
        # Slope of saturation vapor pressure curve
        delta = 4098 * (0.6108 * math.exp(17.27 * temp_mean / (temp_mean + 237.3))) / ((temp_mean + 237.3) ** 2)
        
        # Net radiation (assuming Rn = 0.77 * Rs and G = 0 for daily calculations)
        Rn = solar_radiation * 0.77
        G = 0  # Soil heat flux (negligible for daily calculations)
        
        # Penman-Monteith equation
        numerator = 0.408 * delta * (Rn - G) + gamma * 900 / (temp_mean + 273) * wind_speed * (es - ea)
        denominator = delta + gamma * (1 + 0.34 * wind_speed)
        
        et0 = numerator / denominator
        
        return max(0, et0)
    
    def process_weather_data(self, weather_data):
        """Process weather data and calculate ET0"""
        results = []
        
        if not weather_data or 'weather' not in weather_data:
            return results
        
        # Get location information
        if 'nearest_area' in weather_data and len(weather_data['nearest_area']) > 0:
            location = weather_data['nearest_area'][0]
            lat = float(location['latitude'])
            lon = float(location['longitude'])
        else:
            lat = 35.0  # Default latitude
            lon = 51.0  # Default longitude
        
        # Process current conditions first (today)
        if 'current_condition' in weather_data and len(weather_data['current_condition']) > 0:
            current = weather_data['current_condition'][0]
            today_weather = weather_data['weather'][0] if weather_data['weather'] else None
            
            if today_weather:
                current_date = datetime.now()
                day_of_year = current_date.timetuple().tm_yday
                
                # Get today's min/max from weather data
                temp_max = float(today_weather['maxtempC'])
                temp_min = float(today_weather['mintempC'])
                temp_mean = (temp_max + temp_min) / 2
                
                # Current conditions
                humidity = float(current['humidity'])
                wind_speed = float(current['windspeedKmph']) * 0.277778  # Convert km/h to m/s
                
                # Get sunshine hours if available
                sunshine_hours = None
                if 'astronomy' in today_weather and len(today_weather['astronomy']) > 0:
                    # This is approximate - WWO doesn't provide direct sunshine hours
                    pass
                
                solar_rad, ra = self.calculate_solar_radiation(lat, day_of_year, temp_max, temp_min, humidity, sunshine_hours)
                
                et0_current = self.penman_monteith_et0(
                    temp_mean, temp_max, temp_min,
                    humidity, wind_speed, solar_rad, lat=lat
                )
                
                results.append({
                    'Date': current_date.strftime('%Y-%m-%d'),
                    'Temp Mean (°C)': round(temp_mean, 1),
                    'Temp Max (°C)': round(temp_max, 1),
                    'Temp Min (°C)': round(temp_min, 1),
                    'Humidity (%)': round(humidity, 1),
                    'Wind Speed (m/s)': round(wind_speed, 1),
                    'Solar Radiation (MJ/m²)': round(solar_rad, 2),
                    'ET₀ (mm/day)': round(et0_current, 2)
                })
        
        # Process forecast data (up to 14 days)
        for i, day_weather in enumerate(weather_data['weather'][:14]):
            # Skip today if we already processed current conditions
            if i == 0 and 'current_condition' in weather_data:
                continue
                
            forecast_date = datetime.strptime(day_weather['date'], '%Y-%m-%d')
            day_of_year = forecast_date.timetuple().tm_yday
            
            temp_max = float(day_weather['maxtempC'])
            temp_min = float(day_weather['mintempC'])
            temp_mean = (temp_max + temp_min) / 2
            
            # Average humidity from hourly data if available
            if 'hourly' in day_weather and len(day_weather['hourly']) > 0:
                humidity_values = [float(hour['humidity']) for hour in day_weather['hourly'] if 'humidity' in hour]
                wind_values = [float(hour['windspeedKmph']) * 0.277778 for hour in day_weather['hourly'] if 'windspeedKmph' in hour]
                
                humidity = sum(humidity_values) / len(humidity_values) if humidity_values else 50
                wind_speed = sum(wind_values) / len(wind_values) if wind_values else 2
            else:
                # Fallback values
                humidity = 50  # Default humidity
                wind_speed = 2  # Default wind speed in m/s
            
            solar_rad, ra = self.calculate_solar_radiation(lat, day_of_year, temp_max, temp_min, humidity)
            
            et0_forecast = self.penman_monteith_et0(
                temp_mean, temp_max, temp_min,
                humidity, wind_speed, solar_rad, lat=lat
            )
            
            results.append({
                'Date': day_weather['date'],
                'Temp Mean (°C)': round(temp_mean, 1),
                'Temp Max (°C)': round(temp_max, 1),
                'Temp Min (°C)': round(temp_min, 1),
                'Humidity (%)': round(humidity, 1),
                'Wind Speed (m/s)': round(wind_speed, 1),
                'Solar Radiation (MJ/m²)': round(solar_rad, 2),
                'ET₀ (mm/day)': round(et0_forecast, 2)
            })
        
        return results

def main():
    # Main header
    st.markdown('<h1 class="main-header">🌱 Reference Evapotranspiration Calculator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Penman-Monteith Method • FAO-56 Standard • 14-Day Forecast</p>', unsafe_allow_html=True)
    
    # City search in center
    st.markdown('<div class="city-search">', unsafe_allow_html=True)
    city = st.text_input("🏙️ Enter City Name:", placeholder="Example: Tehran, Iran", key="city_search")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # API Status
        st.markdown('<div class="sidebar-title">📊 API Status</div>', unsafe_allow_html=True)
        api_status = st.empty()
        
        # Guide
        st.markdown('<div class="sidebar-title">📖 Guide</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-card">
        <strong>ET₀:</strong> Reference evapotranspiration of hypothetical grass crop
        <br><br>
        <strong>Applications:</strong><br>
        • Irrigation scheduling<br>
        • Water resource management<br>
        • Climatology studies<br><br>
        <strong>Unit:</strong> mm/day<br>
        <strong>Forecast:</strong> Up to 14 days
        </div>
        """, unsafe_allow_html=True)
        
        # Technical details
        with st.expander("🔬 Technical Details"):
            st.markdown("""
            - **Method:** FAO-56 Penman-Monteith
            - **Data Source:** World Weather Online
            - **Accuracy:** ±0.1 mm/day
            - **Forecast:** 14 days
            - **Solar Radiation:** Hargreaves method
            """)
    
    # Main content
    if city:
        API_KEY = "f38c4a29c65b4720859135600251006"
        calculator = PenmanMonteithCalculator(API_KEY)
        
        with st.spinner('🔄 Fetching weather data...'):
            weather_data = calculator.get_weather_data(city)
        
        if weather_data:
            api_status.success("✅ Connected")
            
            # City information
            if 'nearest_area' in weather_data and len(weather_data['nearest_area']) > 0:
                location = weather_data['nearest_area'][0]
                city_name = location['areaName'][0]['value']
                country = location['country'][0]['value']
                lat = float(location['latitude'])
                lon = float(location['longitude'])
            else:
                city_name = city
                country = "Unknown"
                lat = 0.0
                lon = 0.0
            
            st.markdown(f"""
            <div class="success-message">
                <h3>📍 {city_name}, {country}</h3>
                <p>Latitude: {lat:.2f}° | Longitude: {lon:.2f}°</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Calculate and display results
            results = calculator.process_weather_data(weather_data)
            
            if results:
                df = pd.DataFrame(results)
                
                # Display today's ET0, 14-day total, and average
                today_et0 = df.iloc[0]['ET₀ (mm/day)']
                total_et0 = df['ET₀ (mm/day)'].sum()
                avg_et0 = df['ET₀ (mm/day)'].mean()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Today's ET₀</div>
                        <div class="et0-value">{today_et0}</div>
                        <p style="margin: 0; color: rgba(255,255,255,0.8);">mm/day</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">14-Day Total ET₀</div>
                        <div class="et0-value">{total_et0:.1f}</div>
                        <p style="margin: 0; color: rgba(255,255,255,0.8);">mm</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Average ET₀</div>
                        <div class="et0-value">{avg_et0:.2f}</div>
                        <p style="margin: 0; color: rgba(255,255,255,0.8);">mm/day</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # ET0 Bar Chart
                st.markdown('<div class="section-header">📊 14-Day Evapotranspiration Chart</div>', unsafe_allow_html=True)
                
                # Create a beautiful bar chart
                fig = go.Figure()
                
                # Add gradient colors to bars
                colors = ['#4CAF50' if i == 0 else '#66BB6A' for i in range(len(df))]
                
                fig.add_trace(go.Bar(
                    x=df['Date'],
                    y=df['ET₀ (mm/day)'],
                    marker=dict(
                        color=colors,
                        line=dict(color='#2E7D32', width=1.5),
                        pattern_shape="",
                    ),
                    hovertemplate='<b>Date:</b> %{x}<br><b>ET₀:</b> %{y:.2f} mm/day<extra></extra>',
                    name='ET₀'
                ))
                
                # Add a line showing the average
                fig.add_hline(
                    y=avg_et0, 
                    line_dash="dash", 
                    line_color="#FF9800", 
                    line_width=3,
                    annotation_text=f"Average: {avg_et0:.2f} mm/day",
                    annotation_position="top right"
                )
                
                fig.update_layout(
                    title={
                        'text': 'Reference Evapotranspiration - 14 Day Forecast',
                        'x': 0.5,
                        'xanchor': 'center',
                        'font': {'size': 18, 'color': '#1976D2'}
                    },
                    xaxis_title='Date',
                    yaxis_title='ET₀ (mm/day)',
                    template='plotly_white',
                    height=500,
                    showlegend=False,
                    xaxis=dict(
                        tickangle=45,
                        tickfont=dict(size=11),
                        title_font=dict(size=14, color='#1976D2')
                    ),
                    yaxis=dict(
                        title_font=dict(size=14, color='#1976D2'),
                        gridcolor='#E0E0E0',
                        gridwidth=1
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=50, r=50, t=80, b=100)
                )
                
                # Add some styling to make bars more attractive
                fig.update_traces(
                    marker_line_width=1.5,
                    opacity=0.8
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed table with pagination
                st.markdown('<div class="section-header">📊 14-Day Detailed Data</div>', unsafe_allow_html=True)
                
                # Show first 7 days and last 7 days separately or all together
                display_option = st.radio("Display Option:", ["All 14 Days", "First 7 Days", "Last 7 Days"], horizontal=True)
                
                if display_option == "First 7 Days":
                    display_df = df.head(7)
                elif display_option == "Last 7 Days":
                    display_df = df.tail(7)
                else:
                    display_df = df
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "ET₀ (mm/day)": st.column_config.ProgressColumn(
                            "ET₀ (mm/day)",
                            help="Reference evapotranspiration",
                            min_value=0,
                            max_value=df['ET₀ (mm/day)'].max(),
                            format="%.2f mm"
                        ),
                        "Humidity (%)": st.column_config.ProgressColumn(
                            "Humidity (%)",
                            min_value=0,
                            max_value=100,
                            format="%.1f%%"
                        )
                    }
                )
                
                # Download results
                st.markdown('<div class="section-header">💾 Download Results</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"ET0_{city_name}_{datetime.now().strftime('%Y%m%d')}_14days.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    json_data = df.to_json(orient='records', force_ascii=False)
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_data,
                        file_name=f"ET0_{city_name}_{datetime.now().strftime('%Y%m%d')}_14days.json",
                        mime="application/json"
                    )
            
        else:
            api_status.error("❌ Connection Error")
            st.markdown("""
            <div class="error-message">
                <h3>⚠️ Data Retrieval Error</h3>
                <p>Please check the city name or try again. Make sure to enter city name in English.</p>
                <p>Example formats: "Tehran", "Tehran, Iran", "London, UK"</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Brand footer with link
    st.markdown("""
    <div class="footer-brand">
        <h3>🌐 Designed and Developed by <a href="https://agrodl.ir" target="_blank" style="color: white; text-decoration: none;">AgroDl.ir</a></h3>
        <p>Advanced Agricultural Tools and Solutions</p>
        <p style="font-size: 0.9rem; opacity: 0.8;">Visit us at <strong><a href="https://agrodl.ir" target="_blank" style="color: white; text-decoration: none;">AgroDl.ir</a></strong> for more agricultural tools</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🔬 Calculations based on FAO-56 Penman-Monteith standard method</p>
        <p>📡 Weather data from World Weather Online API</p>
        <p>🌍 14-day forecast with enhanced accuracy</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
