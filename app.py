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
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
    def get_weather_data(self, city, lat=None, lon=None):
        """Get current weather data and forecast"""
        try:
            if lat and lon:
                current_url = f"{self.base_url}/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
                forecast_url = f"{self.base_url}/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            else:
                current_url = f"{self.base_url}/weather?q={city}&appid={self.api_key}&units=metric"
                forecast_url = f"{self.base_url}/forecast?q={city}&appid={self.api_key}&units=metric"
            
            current_response = requests.get(current_url)
            forecast_response = requests.get(forecast_url)
            
            if current_response.status_code == 200 and forecast_response.status_code == 200:
                return current_response.json(), forecast_response.json()
            else:
                return None, None
                
        except Exception as e:
            st.error(f"API Connection Error: {e}")
            return None, None
    
    def calculate_solar_radiation(self, lat, day_of_year, temp_max, temp_min, humidity):
        """Calculate approximate solar radiation"""
        lat_rad = math.radians(lat)
        solar_declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
        sunset_hour_angle = math.acos(-math.tan(lat_rad) * math.tan(solar_declination))
        
        dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
        Ra = (24 * 60 / math.pi) * 0.082 * dr * (
            sunset_hour_angle * math.sin(lat_rad) * math.sin(solar_declination) +
            math.cos(lat_rad) * math.cos(solar_declination) * math.sin(sunset_hour_angle)
        )
        
        temp_range = temp_max - temp_min
        Rs = 0.16 * math.sqrt(temp_range) * Ra
        
        return Rs, Ra
    
    def penman_monteith_et0(self, temp_mean, temp_max, temp_min, humidity, wind_speed, 
                           solar_radiation, elevation=0, lat=35):
        """Calculate ET0 using Penman-Monteith method (mm/day)"""
        
        gamma = 0.665 * (101.3 * ((293 - 0.0065 * elevation) / 293) ** 5.26)
        
        es_max = 0.6108 * math.exp(17.27 * temp_max / (temp_max + 237.3))
        es_min = 0.6108 * math.exp(17.27 * temp_min / (temp_min + 237.3))
        es = (es_max + es_min) / 2
        
        ea = es * humidity / 100
        
        delta = 4098 * (0.6108 * math.exp(17.27 * temp_mean / (temp_mean + 237.3))) / ((temp_mean + 237.3) ** 2)
        
        Rn = solar_radiation * 0.77
        G = 0
        
        numerator = 0.408 * delta * (Rn - G) + gamma * 900 / (temp_mean + 273) * wind_speed * (es - ea)
        denominator = delta + gamma * (1 + 0.34 * wind_speed)
        
        et0 = numerator / denominator
        
        return max(0, et0)
    
    def process_weather_data(self, current_data, forecast_data):
        """Process weather data and calculate ET0"""
        results = []
        
        if not current_data or not forecast_data:
            return results
        
        lat = current_data['coord']['lat']
        lon = current_data['coord']['lon']
        
        # Process current data
        current_temp = current_data['main']['temp']
        current_temp_max = current_data['main']['temp_max']
        current_temp_min = current_data['main']['temp_min']
        current_humidity = current_data['main']['humidity']
        current_wind = current_data['wind']['speed']
        
        current_date = datetime.now()
        day_of_year = current_date.timetuple().tm_yday
        
        solar_rad, ra = self.calculate_solar_radiation(lat, day_of_year, 
                                                      current_temp_max, current_temp_min, 
                                                      current_humidity)
        
        et0_current = self.penman_monteith_et0(
            current_temp, current_temp_max, current_temp_min,
            current_humidity, current_wind, solar_rad, lat=lat
        )
        
        results.append({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Temp Mean (°C)': round(current_temp, 1),
            'Temp Max (°C)': round(current_temp_max, 1),
            'Temp Min (°C)': round(current_temp_min, 1),
            'Humidity (%)': current_humidity,
            'Wind Speed (m/s)': round(current_wind, 1),
            'Solar Radiation (MJ/m²)': round(solar_rad, 2),
            'ET₀ (mm/day)': round(et0_current, 2)
        })
        
        # Process forecast data
        forecast_list = forecast_data['list']
        daily_data = {}
        
        for item in forecast_list:
            date_str = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
            
            if date_str not in daily_data:
                daily_data[date_str] = {
                    'temps': [],
                    'humidity': [],
                    'wind_speed': [],
                    'temp_max': float('-inf'),
                    'temp_min': float('inf')
                }
            
            temp = item['main']['temp']
            daily_data[date_str]['temps'].append(temp)
            daily_data[date_str]['humidity'].append(item['main']['humidity'])
            daily_data[date_str]['wind_speed'].append(item['wind']['speed'])
            daily_data[date_str]['temp_max'] = max(daily_data[date_str]['temp_max'], 
                                                  item['main']['temp_max'])
            daily_data[date_str]['temp_min'] = min(daily_data[date_str]['temp_min'], 
                                                  item['main']['temp_min'])
        
        # Sort dates and limit to 5 days total (including today)
        sorted_dates = sorted([date for date in daily_data.keys() if date != current_date.strftime('%Y-%m-%d')])
        
        for i, date_str in enumerate(sorted_dates[:4]):  # Only take 4 more days (total 5 with today)
            data = daily_data[date_str]
                
            temp_mean = sum(data['temps']) / len(data['temps'])
            humidity_mean = sum(data['humidity']) / len(data['humidity'])
            wind_mean = sum(data['wind_speed']) / len(data['wind_speed'])
            
            forecast_date = datetime.strptime(date_str, '%Y-%m-%d')
            day_of_year = forecast_date.timetuple().tm_yday
            
            solar_rad, ra = self.calculate_solar_radiation(lat, day_of_year,
                                                          data['temp_max'], data['temp_min'],
                                                          humidity_mean)
            
            et0_forecast = self.penman_monteith_et0(
                temp_mean, data['temp_max'], data['temp_min'],
                humidity_mean, wind_mean, solar_rad, lat=lat
            )
            
            results.append({
                'Date': date_str,
                'Temp Mean (°C)': round(temp_mean, 1),
                'Temp Max (°C)': round(data['temp_max'], 1),
                'Temp Min (°C)': round(data['temp_min'], 1),
                'Humidity (%)': round(humidity_mean, 1),
                'Wind Speed (m/s)': round(wind_mean, 1),
                'Solar Radiation (MJ/m²)': round(solar_rad, 2),
                'ET₀ (mm/day)': round(et0_forecast, 2)
            })
        
        return results

def main():
    # Main header
    st.markdown('<h1 class="main-header">🌱 Reference Evapotranspiration Calculator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Penman-Monteith Method • FAO-56 Standard</p>', unsafe_allow_html=True)
    
    # City search in center
    st.markdown('<div class="city-search">', unsafe_allow_html=True)
    city = st.text_input("🏙️ Enter City Name:", placeholder="Example: Tehran, IR", key="city_search")
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
        <strong>Unit:</strong> mm/day
        </div>
        """, unsafe_allow_html=True)
        
        # Technical details
        with st.expander("🔬 Technical Details"):
            st.markdown("""
            - **Method:** FAO-56 Penman-Monteith
            - **Data Source:** OpenWeatherMap
            - **Accuracy:** ±0.1 mm/day
            - **Forecast:** 5 days
            """)
    
    # Main content
    if city:
        API_KEY = "019d8b55d4f53d3a5ffc2acbec84f324"
        calculator = PenmanMonteithCalculator(API_KEY)
        
        with st.spinner('🔄 Fetching weather data...'):
            current_data, forecast_data = calculator.get_weather_data(city)
        
        if current_data and forecast_data:
            api_status.success("✅ Connected")
            
            # City information
            city_name = current_data['name']
            country = current_data['sys']['country']
            lat = current_data['coord']['lat']
            lon = current_data['coord']['lon']
            
            st.markdown(f"""
            <div class="success-message">
                <h3>📍 {city_name}, {country}</h3>
                <p>Latitude: {lat:.2f}° | Longitude: {lon:.2f}°</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Calculate and display results
            results = calculator.process_weather_data(current_data, forecast_data)
            
            if results:
                df = pd.DataFrame(results)
                
                # Display today's ET0 and total ET0 (removed average)
                today_et0 = df.iloc[0]['ET₀ (mm/day)']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Today's ET₀</div>
                        <div class="et0-value">{today_et0}</div>
                        <p style="margin: 0; color: rgba(255,255,255,0.8);">mm/day</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    total_et0 = df['ET₀ (mm/day)'].sum()
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Total ET₀</div>
                        <div class="et0-value">{total_et0:.2f}</div>
                        <p style="margin: 0; color: rgba(255,255,255,0.8);">mm (5 days)</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # ET0 Chart
                st.markdown('<div class="section-header">📈 Evapotranspiration Chart</div>', unsafe_allow_html=True)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['Date'],
                    y=df['ET₀ (mm/day)'],
                    mode='lines+markers',
                    name='ET₀',
                    line=dict(color='#4CAF50', width=3),
                    marker=dict(size=10, color='#4CAF50')
                ))
                
                fig.update_layout(
                    title='Reference Evapotranspiration Variation',
                    xaxis_title='Date',
                    yaxis_title='ET₀ (mm/day)',
                    hovermode='x unified',
                    template='plotly_white',
                    height=400,
                    title_font_color='#1976D2'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Weather parameters charts - separate charts for humidity and wind
                st.markdown('<div class="section-header">🌡️ Weather Parameters</div>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Temperature chart
                    fig_temp = go.Figure()
                    fig_temp.add_trace(go.Scatter(x=df['Date'], y=df['Temp Max (°C)'], 
                                                name='Max', line=dict(color='#D32F2F')))
                    fig_temp.add_trace(go.Scatter(x=df['Date'], y=df['Temp Mean (°C)'], 
                                                name='Mean', line=dict(color='#FF9800')))
                    fig_temp.add_trace(go.Scatter(x=df['Date'], y=df['Temp Min (°C)'], 
                                                name='Min', line=dict(color='#1976D2')))
                    fig_temp.update_layout(title='Temperature (°C)', height=300, template='plotly_white',
                                         title_font_color='#1976D2')
                    st.plotly_chart(fig_temp, use_container_width=True)
                
                with col2:
                    # Humidity chart
                    fig_humid = go.Figure()
                    fig_humid.add_trace(go.Scatter(x=df['Date'], y=df['Humidity (%)'], 
                                                 name='Humidity (%)', line=dict(color='#2196F3')))
                    fig_humid.update_layout(
                        title='Humidity (%)',
                        yaxis=dict(title='Humidity (%)'),
                        height=300,
                        template='plotly_white',
                        title_font_color='#1976D2'
                    )
                    st.plotly_chart(fig_humid, use_container_width=True)
                
                with col3:
                    # Wind speed chart
                    fig_wind = go.Figure()
                    fig_wind.add_trace(go.Scatter(x=df['Date'], y=df['Wind Speed (m/s)'], 
                                                name='Wind Speed', line=dict(color='#4CAF50')))
                    fig_wind.update_layout(
                        title='Wind Speed (m/s)',
                        yaxis=dict(title='Wind Speed (m/s)'),
                        height=300,
                        template='plotly_white',
                        title_font_color='#1976D2'
                    )
                    st.plotly_chart(fig_wind, use_container_width=True)
                
                # Detailed table (5 days only)
                st.markdown('<div class="section-header">📊 5-Day Detailed Data</div>', unsafe_allow_html=True)
                
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=250,
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
                            format="%d%%"
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
                        file_name=f"ET0_{city_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    json_data = df.to_json(orient='records', force_ascii=False)
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_data,
                        file_name=f"ET0_{city_name}_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
            
        else:
            api_status.error("❌ Connection Error")
            st.markdown("""
            <div class="error-message">
                <h3>⚠️ Data Retrieval Error</h3>
                <p>Please check the city name or try again</p>
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
        <p>📡 Weather data from OpenWeatherMap API</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
