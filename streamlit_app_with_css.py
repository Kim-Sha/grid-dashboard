#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import datetime

#######################
# Page configuration
st.set_page_config(
    page_title="GRID: Plug Load Management",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed")

alt.themes.enable("dark")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)


#######################
# Load data
df_reshaped = pd.read_csv('data/us-population-2010-2019-reshaped.csv')

df = pd.read_parquet('./data/smart_plug_energy_use.parquet')

# fucking with the data
df_before = df[df.date < '2024-04-20']
df_before['date'] = df_before['date'] + pd.Timedelta('10D20H')
df_after = df[df.date > '2024-04-28']
# Join before/after traces
df_concat = pd.concat([df_before, df_after])
# Raw consumption plot by device
fig_raw = px.bar(df_concat.groupby([pd.Grouper(key='date', freq='H'), 'source']).kwh.sum().reset_index(),
                 x='date', y='kwh', color='source',
                 title='Raw Energy Consumption Feed',
                 labels = {'kwh':'Energy Use (kWh)', 'source':'Source', 'date':'Date'})

# More massaging the data
df_concat = df_concat.groupby([pd.Grouper(key='date', freq='1H')]).kwh.sum().reset_index()
df_concat['schedule'] = df_concat.kwh.copy()
df_concat.loc[df_concat.date.dt.hour.between(0, 5), 'schedule'] = 0
df_concat = df_concat.rename(columns={'kwh':'Regular', 'schedule': 'Schedule'})
df_concat = df_concat.melt(id_vars=['date'], value_vars=['Regular', 'Schedule'])
# Allowing spline interpolation even for scheduled periods
df_concat = df_concat[~((df_concat.variable=='Regular')&(df_concat.date.dt.hour.between(0, 5))&(df_concat.date > '2024-04-29 12:00:00'))]

#######################
# Sidebar
with st.sidebar:
    st.image('logo.png')
    st.title('GRID: Plug Load Management')
    
    year_list = list(df_reshaped.year.unique())[::-1]
    
    selected_year = st.selectbox('Select a Year', year_list)
    df_selected_year = df_reshaped[df_reshaped.year == selected_year]
    df_selected_year_sorted = df_selected_year.sort_values(by="population", ascending=False)

    color_theme_list = ['Bloomberg', 'Tata', 'Verizon']
    selected_color_theme = st.selectbox('Select a facility', color_theme_list)


#######################
# Plots

# Smoothed total energy consumption comparison plot
fig = px.line(df_concat.groupby([pd.Grouper(key='date', freq='1H'), 'variable']).value.sum().reset_index()\
                       .sort_values(by=['variable', 'date'], ascending=[False, True]),
              x='date', y='value', color='variable', line_shape='spline',# height=500,
              color_discrete_sequence=['limegreen', 'orangered'],
              title='Total Energy Use',
              labels={'kwh': 'Energy Use (kWh)', 'date':'Date', 'variable':'', 'value': 'Energy Use (kWh)'})
fig['data'][0]['line']['dash'] = 'dash'

# Heatmap
def make_heatmap(input_df, input_y, input_x, input_color, input_color_theme):
    heatmap = alt.Chart(input_df).mark_rect().encode(
            y=alt.Y(f'{input_y}:O', axis=alt.Axis(title="Year", titleFontSize=18, titlePadding=15, titleFontWeight=900, labelAngle=0)),
            x=alt.X(f'{input_x}:O', axis=alt.Axis(title="", titleFontSize=18, titlePadding=15, titleFontWeight=900)),
            color=alt.Color(f'max({input_color}):Q',
                             legend=None,
                             scale=alt.Scale(scheme=input_color_theme)),
            stroke=alt.value('black'),
            strokeWidth=alt.value(0.25),
        ).properties(width=900
        ).configure_axis(
        labelFontSize=12,
        titleFontSize=12
        ) 
    # height=300
    return heatmap

# Choropleth map
def make_choropleth(input_df, input_id, input_column, input_color_theme):
    choropleth = px.choropleth(input_df, locations=input_id, color=input_column, locationmode="USA-states",
                               color_continuous_scale=input_color_theme,
                               range_color=(0, max(df_selected_year.population)),
                               scope="usa",
                               labels={'population':'Population'}
                              )
    choropleth.update_layout(
        template='plotly_dark',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=350
    )
    return choropleth


# Donut chart
def make_donut(input_response, input_text, input_color):
  if input_color == 'blue':
      chart_color = ['#29b5e8', '#155F7A']
  if input_color == 'green':
      chart_color = ['#27AE60', '#12783D']
  if input_color == 'orange':
      chart_color = ['#F39C12', '#875A12']
  if input_color == 'red':
      chart_color = ['#E74C3C', '#781F16']
    
  source = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100-input_response, input_response]
  })
  source_bg = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100, 0]
  })
    
  plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=25).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          #domain=['A', 'B'],
                          domain=[input_text, ''],
                          # range=['#29b5e8', '#155F7A']),  # 31333F
                          range=chart_color),
                      legend=None),
  ).properties(width=130, height=130)
    
  text = plot.mark_text(align='center', color="#29b5e8", font="Lato", fontSize=32, fontWeight=700, fontStyle="normal").encode(text=alt.value(f'{input_response} %'))
  plot_bg = alt.Chart(source_bg).mark_arc(innerRadius=45, cornerRadius=20).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          # domain=['A', 'B'],
                          domain=[input_text, ''],
                          range=chart_color),  # 31333F
                      legend=None),
  ).properties(width=130, height=130)
  return plot_bg + plot + text

# Convert population to text 
def format_number(num):
    if num > 1000000:
        if not num % 1000000:
            return f'{num // 1000000} M'
        return f'{round(num / 1000000, 1)} M'
    return f'{num // 1000} K'

# Calculation year-over-year population migrations
def calculate_population_difference(input_df, input_year):
  selected_year_data = input_df[input_df['year'] == input_year].reset_index()
  previous_year_data = input_df[input_df['year'] == input_year - 1].reset_index()
  selected_year_data['population_difference'] = selected_year_data.population.sub(previous_year_data.population, fill_value=0)
  return pd.concat([selected_year_data.states, selected_year_data.id, selected_year_data.population, selected_year_data.population_difference], axis=1).sort_values(by="population_difference", ascending=False)


#######################
# Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap='medium')

with col[0]:
    st.markdown('#### Savings')
    
    df_population_difference_sorted = calculate_population_difference(df_reshaped, selected_year)
    
    if selected_year > 2010:
        first_state_name = "Money Saved"
        first_state_population = "$1.31"
        first_state_delta = "1.31"
    else:
        first_state_name = '-'
        first_state_population = '-'
        first_state_delta = ''
    st.metric(label=first_state_name, value=first_state_population, delta=first_state_delta)

    if selected_year > 2010:
        last_state_name = "kWh Saved"
        last_state_population = "4.53"
        last_state_delta = "4.53"
    else:
        last_state_name = '-'
        last_state_population = '-'
        last_state_delta = ''
    st.metric(label=last_state_name, value=last_state_population, delta=last_state_delta)
    
    
    st.markdown('#### System Stats')

    if selected_year > 2010:
        # Filter states with population difference > 50000
        # df_greater_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference_absolute > 50000]
        df_greater_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference > 50000]
        df_less_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference < -50000]
        
        # % of States with population difference > 50000
        states_migration_greater = round((len(df_greater_50000)/df_population_difference_sorted.states.nunique())*100)
        states_migration_less = round((len(df_less_50000)/df_population_difference_sorted.states.nunique())*100)
        donut_chart_greater = make_donut(29, 'Inbound Migration', 'green')
        donut_chart_less = make_donut(18, 'Outbound Migration', 'blue')
        donut_chart_less1 = make_donut(99.9, 'Outbound Migration', 'orange')
    else:
        states_migration_greater = 0
        states_migration_less = 0
        donut_chart_greater = make_donut(29, 'Inbound Migration', 'blue')
        donut_chart_less = make_donut(1, 'Outbound Migration', 'green')
        donut_chart_less = make_donut(1, 'Outbound Migration', 'green')

    migrations_col = st.columns((0.2, 1, 0.2))
    with migrations_col[1]:
        st.write('Percent Time Offline')
        st.altair_chart(donut_chart_greater)
        st.write('Percent Energy Saved')
        st.altair_chart(donut_chart_less)
        st.write('System Uptime')
        st.altair_chart(donut_chart_less1)
        #st.metric(label="kWh Projected", value=551, delta=+8,
        #delta_color="normal")

        #st.metric(label="Money Projected", value="$160", delta=+2,
        #delta_color="normal")

with col[1]:
    st.markdown('#### Summary of Energy Consumption')

    st.plotly_chart(fig, use_container_width=True)
    st.plotly_chart(fig_raw, use_container_width=True)
    
    # choropleth = make_choropleth(df_selected_year, 'states_code', 'population', selected_color_theme)
    # st.plotly_chart(choropleth, use_container_width=True)
    
    # heatmap = make_heatmap(df_reshaped, 'year', 'states', 'population', selected_color_theme)
    # st.altair_chart(heatmap, use_container_width=True)
    

with col[2]:
    st.markdown('#### Your Devices')

    st.dataframe(df_selected_year_sorted,
                 column_order=("states", "population"),
                 hide_index=True,
                 width=None,
                 column_config={
                    "states": st.column_config.TextColumn(
                        "Device",
                    ),
                    "population": st.column_config.ProgressColumn(
                        "Projected Usage (kWh)",
                        format="%f",
                        min_value=0,
                        max_value=max(df_selected_year_sorted.population),
                     )}
                 )
    

    

    with st.expander('Control Panel', expanded=True):
        st.toggle('Toggle Smart Scheduling')
        #def time_input():
        #    t = st.time_input("Start Time", datetime.time(21, 00))
        #    t1 = st.time_input("End Time", datetime.time(7, 00))
        #st.button('Customize Schedule', use_container_width=True, disabled=False)

        if st.button("Customize Schedule", use_container_width=True):
            t = st.time_input("Start Time", datetime.time(21, 00))
            t1 = st.time_input("End Time", datetime.time(7, 00))
        

        st.write("Need help? Contact [support](https://docs.streamlit.io/)!")
        
