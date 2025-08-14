import matplotlib
matplotlib.use('Agg')

from flask import Flask, request, render_template
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pycountry
import io, base64

app = Flask(__name__)

#--------------------------------------------------------------------------------------------------------

# to make sure the countries of the two dataframes match
def code_to_name(code):

    special_cases = {
        "BO": "Bolivia (Plurinational State of)",
        "VG": "British Virgin Islands",
        "CI": "Côte d’Ivoire",
        "KP": "Democratic People's Republic of Korea",
        "CD": "Democratic Republic of the Congo",
        "IR": "Iran (Islamic Republic of)",
        "NL": "Netherlands (Kingdom of the)",
        "KR": "Republic of Korea",
        "MD": "Republic of Moldova",
        "PS": "State of Palestine",
        "TW": "Taiwan (Province of China)",
        "GB": "United Kingdom of Great Britain and Northern Ireland",
        "TZ": "United Republic of Tanzania",
        "US": "United States of America",
        "VE": "Venezuela (Bolivarian Republic of)"
}
    if code in special_cases:
        return special_cases[code]
    
    try:
        country = pycountry.countries.get(alpha_2=code)
        return country.name if country else code
    except:
        return code
    
#--------------------------------------------------------------------------------------------------------

# data frame for the graph
merged_disaster = pd.read_csv('merged_disaster1.csv')
cross_tier = pd.read_csv('cross_tier_GB_only_deduplicated1.xls')
country_list = sorted(merged_disaster.groupby("Country").count().index)
cross_tier['First_Tier_Country'] = cross_tier['First_Tier_Country'].apply(code_to_name)
cross_tier['Second_Tier_Country'] = cross_tier['Second_Tier_Country'].apply(code_to_name)

#--------------------------------------------------------------------------------------------------------

#to get graph for total disaster over years organized by type
merged_disaster_total = merged_disaster.groupby(["Start Year", "Disaster Type"]).count()[[
"DisNo."]].reset_index()
merged_disaster_total['Start Year'] = merged_disaster_total['Start Year'].astype(int)
merged_disaster_total = merged_disaster_total[merged_disaster_total['Start Year'] <= 2023]

#to get graph for total supplier count over years
cross_tier_total = cross_tier[(cross_tier["YEAR"] >= 2010) & (cross_tier["YEAR"] < 2024)]

cross_tier_total_first = cross_tier_total.groupby(["YEAR", 
        "First_Tier_Supplier"]).count().reset_index().groupby(
        "YEAR").count()[["First_Tier_Supplier"]].reset_index()

cross_tier_total_second = cross_tier_total.groupby(["YEAR"]).count()[["Second_Tier_Supplier"]].reset_index()

merged_cross_first_second_total = pd.merge(cross_tier_total_second, 
                                     cross_tier_total_first, on = "YEAR", how = 'inner')
        
#--------------------------------------------------------------------------------------------------------
def make_disaster_total_plot():
    #pivot total disaster plot
    pivot_merged_disaster_total = merged_disaster_total.pivot_table(
    index='Start Year',
    columns='Disaster Type',
    values='DisNo.',
    aggfunc='sum',
    fill_value=0)

    fig_disaster_total, ax_disaster_total = plt.subplots(figsize=(12,6))

    pivot_merged_disaster_total.plot(
    kind='bar',
    stacked=True,
    ax = ax_disaster_total)

    ax_disaster_total.set_title('Number of Disasters by Type per Year in Total')
    ax_disaster_total.set_xlabel('Year')
    ax_disaster_total.set_xticklabels(ax_disaster_total.get_xticklabels(), rotation=0)
    ax_disaster_total.set_ylabel('Number of Disasters')
    ax_disaster_total.legend(title='Disaster Type', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    img_disaster_total = io.BytesIO()
    fig_disaster_total.savefig(img_disaster_total, format='png')
    plt.close(fig_disaster_total)  # Close the figure to free memory
    img_disaster_total.seek(0)

    # Encode to base64 string for embedding in HTML
    plot_url_disaster_total = base64.b64encode(img_disaster_total.getvalue()).decode()
    return plot_url_disaster_total

def make_cross_total_plot():
    #supplier count graph
    x_total = np.arange(len(merged_cross_first_second_total['YEAR']))  # positions for each year
    width = 0.3  # width of bars

    fig_cross_total, ax1_total = plt.subplots(figsize=(12,6))

    # First axis (disaster count)
    ax1_total.bar(x_total - width, merged_cross_first_second_total['First_Tier_Supplier'], width=width, label='First Tier Supplier', color='skyblue')
    ax1_total.set_xlabel('Year')
    ax1_total.set_ylabel('First Tier Supplier', color='black')
    ax1_total.set_xticks(x_total)
    ax1_total.set_xticklabels(merged_cross_first_second_total['YEAR'])
    ax1_total.tick_params(axis='y', labelcolor='black')

    # Second axis (supplier counts)        
    ax2_total = ax1_total.twinx()
    ax2_total.bar(x_total + width, merged_cross_first_second_total['Second_Tier_Supplier'], width=width, label='Second Tier Supplier', color='green')        
    ax2_total.set_ylabel('Second Tier Supplier', color='black')
    ax2_total.tick_params(axis='y', labelcolor='black')        

    ax1_total.set_title('First and Second Tier Supplier Count by Year')
    fig_cross_total.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9))
    plt.tight_layout()

    img_cross_total = io.BytesIO()
    fig_cross_total.savefig(img_cross_total, format='png')
    plt.close(fig_cross_total)  # Close the figure to free memory        
    img_cross_total.seek(0)

    # Encode to base64 string for embedding in HTML
    plot_url_cross_total = base64.b64encode(img_cross_total.getvalue()).decode()
    return plot_url_cross_total
#--------------------------------------------------------------------------------------------------------

plot_url_disaster_total = make_disaster_total_plot()
plot_url_cross_total = make_cross_total_plot()

@app.route('/', methods = ['GET', 'POST'])
def index():
    chosen_country = None
    plot_url_disaster = None
    plot_url_first = None
    plot_url_second = None
    data_available_first = False
    data_available_second = False
    correlation_first = None
    correlation_second = None

    if request.method == 'POST':
        chosen_country = request.form.get('country')

    #--------------------------------------------------------------------------------------------------------
        
        #disaster dataframe filtered by country and year less than 2024
        merged_disaster_country = merged_disaster[(merged_disaster["Country"] == chosen_country) & 
(merged_disaster["Start Year"] < 2024)].groupby(["Start Year", "Disaster Type"]).count()[[
"DisNo."]].reset_index()
        merged_disaster_country['Start Year'] = merged_disaster_country['Start Year'].astype(int)
    
        #supplier dataframe filtered by country and year
        cross_tier_country = cross_tier[(cross_tier["First_Tier_Country"] == chosen_country) 
| (cross_tier["Second_Tier_Country"] == chosen_country)]
        cross_tier_country = cross_tier_country[(cross_tier_country["YEAR"] >= 2010) & 
(cross_tier_country["YEAR"] < 2024)]
   
        #first tier supplier dataframe
        cross_tier_country_first = cross_tier_country.groupby(["YEAR", 
"First_Tier_Supplier"]).count().reset_index().groupby(
"YEAR").count()[["First_Tier_Supplier"]].reset_index()
    
        #second tier supplier dataframe
        cross_tier_country_second = cross_tier_country.groupby(["YEAR"]).count()[["Second_Tier_Supplier"]].reset_index()

    #--------------------------------------------------------------------------------------------------------
    
        #pivot disaster plot
        pivot_merged_disaster_country = merged_disaster_country.pivot_table(
        index='Start Year',
        columns='Disaster Type',
        values='DisNo.',
        aggfunc='sum',
        fill_value=0)
    
        #Start of Disaster Count Graph
        fig_disaster, ax_disaster = plt.subplots(figsize=(12, 6))

        pivot_merged_disaster_country.plot(
        kind='bar',
        stacked=True,
        ax = ax_disaster)

        ax_disaster.set_title('Number of Disasters by Type per Year in ' + chosen_country)
        ax_disaster.set_xlabel('Year')
        ax_disaster.set_xticklabels(ax_disaster.get_xticklabels(), rotation=0)
        ax_disaster.set_ylabel('Number of Disasters')
        ax_disaster.legend(title='Disaster Type', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()

        # Save plot to a bytes buffer instead of showing
        img_disaster = io.BytesIO()
        fig_disaster.savefig(img_disaster, format='png')
        plt.close(fig_disaster)  # Close the figure to free memory
        img_disaster.seek(0)

        # Encode to base64 string for embedding in HTML
        plot_url_disaster = base64.b64encode(img_disaster.getvalue()).decode()
    
    #--------------------------------------------------------------------------------------------------------

        #Start of First Tier Supplier Graph
        # Set up bar positions for first tier supplier
        if not cross_tier_country_first.empty:
            data_available_first = True
        
        x_first = np.arange(len(cross_tier_country_first['YEAR']))  # positions for each year
        width_first = 0.6  # width of bars

        fig_first, ax_first = plt.subplots(figsize=(12,6))

        # First Tier Supplier axis
        ax_first.bar(x_first,
                  cross_tier_country_first['First_Tier_Supplier'],
                  width=width_first,
                  label='First Tier Supplier',
                  color='skyblue')
        ax_first.set_xlabel('Year')
        ax_first.set_ylabel('First Tier Supplier', color='black')
        ax_first.set_xticks(x_first)
        ax_first.set_xticklabels(cross_tier_country_first['YEAR'])
        ax_first.tick_params(axis='y', labelcolor='black')
        ax_first.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax_first.set_title('First Tier Supplier Count in ' + chosen_country + ' by Year')
        plt.tight_layout()

        img_first = io.BytesIO()
        fig_first.savefig(img_first, format='png')
        plt.close(fig_first)  # Close the figure to free memory
        img_first.seek(0)

        # Encode to base64 string for embedding in HTML
        plot_url_first = base64.b64encode(img_first.getvalue()).decode()

    #--------------------------------------------------------------------------------------------------------

        #Start of Second Tier Supplier Graphs
        if not cross_tier_country_first.empty:
            data_available_second = True
        x_second = np.arange(len(cross_tier_country_second['YEAR']))  # positions for each year
        width_second = 0.6  # width of bars

        fig_second, ax_second = plt.subplots(figsize=(12,6))

        # Second Tier Supplier axis
        ax_second.bar(x_second,
                  cross_tier_country_second['Second_Tier_Supplier'],
                  width=width_second,
                  label='Second Tier Supplier',
                  color='darkgreen')
        ax_second.set_xlabel('Year')
        ax_second.set_ylabel('Second Tier Supplier', color='black')
        ax_second.set_xticks(x_second)
        ax_second.set_xticklabels(cross_tier_country_second['YEAR'])
        ax_second.tick_params(axis='y', labelcolor='black')
        ax_second.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax_second.set_title('Second Tier Supplier Count in ' + chosen_country + ' by Year')
        plt.tight_layout()

        img_second = io.BytesIO()
        fig_second.savefig(img_second, format='png')
        plt.close(fig_second)  # Close the figure to free memory
        img_second.seek(0)

        # Encode to base64 string for embedding in HTML
        plot_url_second = base64.b64encode(img_second.getvalue()).decode()

    #--------------------------------------------------------------------------------------------------------

        #correlation
        #data frame for all disaster count of a country
        merged_disaster_country_together = merged_disaster_country.groupby("Start Year").sum()
        #data frame for first tier supplier
        equation_df_first = pd.merge(merged_disaster_country_together, cross_tier_country_first, left_on = "Start Year",
                       right_on = "YEAR")
        equation_df_first = equation_df_first.dropna()
        #data frame for second tier supplier
        equation_df_second = pd.merge(merged_disaster_country_together, cross_tier_country_second, left_on = "Start Year",
                       right_on = "YEAR")
        equation_df_second = equation_df_second.dropna()

        # Calculate correlation for first tier if data is available
        if data_available_first and not equation_df_first.empty:
            correlation_first = equation_df_first['DisNo.'].corr(equation_df_first['First_Tier_Supplier'])

        # Calculate correlation for second tier if data is available
        if data_available_second and not equation_df_second.empty:
            correlation_second = equation_df_second['DisNo.'].corr(equation_df_second['Second_Tier_Supplier'])
    
    return render_template(
        "index.html",
        chosen_country = chosen_country,
        countries = country_list,
        data_available_first = data_available_first,
        data_available_second = data_available_second,
        correlation_first = correlation_first,
        correlation_second = correlation_second,
        plot_url_disaster=plot_url_disaster,
        plot_url_first = plot_url_first,
        plot_url_second = plot_url_second,
        plot_url_disaster_total = plot_url_disaster_total,
        plot_url_cross_total = plot_url_cross_total
    )

#--------------------------------------------------------------------------------------------------------

@app.route("/second")
def second_page():

    return render_template(
        "second.html",
        plot_url_disaster_total = plot_url_disaster_total,
        plot_url_cross_total = plot_url_cross_total                  
        )  # new page

@app.route("/heatmap")
def heatmap():
    return render_template("heatmap.html")

if __name__ == '__main__':
    app.run(debug=True)


    

