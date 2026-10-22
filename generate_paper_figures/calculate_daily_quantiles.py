#Abigail Birnbaum
#script to calculate daily quantiles for selected HUC2 region
#Last updated: 2026-08-25

#import required packages
import os
import pandas as pd
import numpy as np
import xarray as xr
import joblib

########################################################################################
#################################### Define Methods ####################################
########################################################################################

def calculate_daily_quantiles(vic_dp,reg_sel,scen_name,rank_lo,rank_hi):
    """ 
    What function does.

    Inputs:
    vic_dp:
    reg_sel:
    scen_name:
    rank_lo:
    rank_hi:
    
    Outputs: 
    """
    print('loading in data for region: '+reg_sel+', scenario: '+scen_name)
    daily_output_reg_scen = xr.open_dataset(vic_dp+reg_sel+'/daily_vic_'+reg_sel+'_'+scen_name+'.nc')
    daily_output_reg_scen['vic_qf_bf'] = daily_output_reg_scen['vic_qf']+daily_output_reg_scen['vic_bf'] #sum qf and bf
    daily_df = daily_output_reg_scen['vic_qf_bf'].to_dataframe().reset_index() #convert to dataframe
    #clean up dataframe
    daily_df = daily_df.reset_index().drop(columns=['index'])
    daily_df['region2'] = daily_df['basin'].str[:2]
    daily_df['time'] = pd.to_datetime(daily_df['time'])
    #get year/month
    daily_df['year'] = daily_df.time.dt.year
    daily_df['month'] = daily_df.time.dt.month
 
    # 7Q10min calculation: annual minimum 7-day mean runoff
    print('calculating 7q10-min: min 7-day mean flow for 10-year return period')
    #calculate 7-day rolling mean for each basin and scenario
    df_roll_7dmean = daily_df.groupby(['basin','scenario','region2'])['vic_qf_bf'].rolling(7).mean().reset_index()
    #add back in columns for time, year, month
    df_roll_7dmean['time'] = daily_df['time'].copy()
    df_roll_7dmean['year'] = daily_df['year'].copy()
    #for each basin, year get minimum 7-day mean daily flow
    df_7dmin = df_roll_7dmean.groupby(['region2','basin','scenario','year'])['vic_qf_bf'].min().reset_index()
    df_7dmin['rank_val'] = df_7dmin.groupby(['region2','basin','scenario'])['vic_qf_bf'].rank(ascending=True,method='first')
    n = len(df_7dmin.year.unique())
    df_7dmin['return_interval'] = (n+1)/df_7dmin['rank_val']
    df_7dmin['p_exc'] = 1/df_7dmin['return_interval']
    #linear interpolate between the closest values to pexc = 10%
    p_exc_lo =  rank_lo/(n+1)
    df_7q_lo = df_7dmin[df_7dmin.rank_val==rank_lo]
    p_exc_hi = rank_hi/(n+1)
    df_7q_hi = df_7dmin[df_7dmin.rank_val==rank_hi]
    df_7q10min = df_7q_lo.merge(df_7q_hi,on=['region2','basin','scenario'],suffixes=['_lo','_hi'])
    df_7q10min['p_exc_diff'] = df_7q10min['p_exc_hi'] - df_7q10min['p_exc_lo']
    df_7q10min['vic_qf_bf_diff'] = df_7q10min['vic_qf_bf_hi'] - df_7q10min['vic_qf_bf_lo']
    df_7q10min['m_interp'] = df_7q10min['vic_qf_bf_diff']/df_7q10min['p_exc_diff']
    df_7q10min['b_interp'] = df_7q10min['vic_qf_bf_hi'] - (df_7q10min['m_interp']*df_7q10min['p_exc_hi'])
    df_7q10min['vic_7q10min'] = df_7q10min['m_interp']*(0.1) + df_7q10min['b_interp']
    df_7q10min = df_7q10min.filter(['region2','basin','scenario','vic_7q10min']) #clean up output

    # 5Q10max calculation: annual maximum 5-day sum runoff
    print('calculating 5q10-max: max 5-day flow for 10-year return period')
    #calculate 5-day rolling sum for each basin and scenario
    df_roll_5dsum = daily_df.groupby(['basin','scenario','region2'])['vic_qf_bf'].rolling(5).sum().reset_index()
    #add back in columns for time, year, month
    df_roll_5dsum['time'] = daily_df['time'].copy()
    df_roll_5dsum['year'] = daily_df['year'].copy()
    #for each basin, year get max 5-day sum daily flow
    df_5dmax = df_roll_5dsum.groupby(['region2','basin','scenario','year'])['vic_qf_bf'].max().reset_index()
    df_5dmax['rank_val'] = df_5dmax.groupby(['region2','basin','scenario'])['vic_qf_bf'].rank(ascending=False,method='first')
    n = len(df_5dmax.year.unique())
    df_5dmax['return_interval'] = (n+1)/df_5dmax['rank_val']
    df_5dmax['p_exc'] = 1/df_5dmax['return_interval']
    #linear interpolate between the closest values to pexc = 10%
    p_exc_lo =  rank_lo/(n+1)
    df_5q_lo = df_5dmax[df_5dmax.rank_val==rank_lo]
    p_exc_hi = rank_hi/(n+1)
    df_5q_hi = df_5dmax[df_5dmax.rank_val==rank_hi]
    df_5q10max = df_5q_lo.merge(df_5q_hi,on=['region2','basin','scenario'],suffixes=['_lo','_hi'])
    df_5q10max['p_exc_diff'] = df_5q10max['p_exc_hi'] - df_5q10max['p_exc_lo']
    df_5q10max['vic_qf_bf_diff'] = df_5q10max['vic_qf_bf_hi'] - df_5q10max['vic_qf_bf_lo']
    df_5q10max['m_interp'] = df_5q10max['vic_qf_bf_diff']/df_5q10max['p_exc_diff']
    df_5q10max['b_interp'] = df_5q10max['vic_qf_bf_hi'] - (df_5q10max['m_interp']*df_5q10max['p_exc_hi'])
    df_5q10max['vic_5q10max'] = df_5q10max['m_interp']*(0.1) + df_5q10max['b_interp']
    df_5q10max = df_5q10max.filter(['region2','basin','scenario','vic_5q10max']) #clean up output

    return df_7q10min, df_5q10max

########################################################################################
################################### Define Variables ###################################
########################################################################################

# list of regions
#reg_list = ['huc01','huc02','huc03','huc04','huc05','huc06','huc07','huc08','huc09','huc10','huc11','huc12',
#            'huc13','huc14','huc15','huc16','huc17','huc18','pfaf71','pfaf72','pfaf73','pfaf75','pfaf77','pfaf78']

# list of scenarios
scen_list = ['era5d','ic0_fhist','ic1_fhist','ic2_fhist','ic3_fhist','ic4_fhist','ic5_fhist','ic6_fhist','ic7_fhist','ic8_fhist','ic9_fhist']

# paths to data
pwp = '/gcfs/projects/foresight/hydrology/'
vic_dp = pwp+abirn_vic/final_vic_output/' #VIC output - ERA5D and ACE2
save_path = pwp+'abirn_vic/vic_output_analysis/saved_data/daily_quantiles/'

# define variables
reg_sel = 'huc13'
rank_lo = 4
rank_hi = 5

##############################################################################################################
#################################################### MAIN ####################################################
##############################################################################################################

if __name__ == '__main__':
    quantiles_res = joblib.Parallel(n_jobs=8)(joblib.delayed(calculate_daily_quantiles)(vic_dp, reg_sel,scen_list[i],rank_lo,rank_hi) for i in range(len(scen_list)))            
    low_qs = [pair[0] for pair in quantiles_res]
    high_qs = [pair[1] for pair in quantiles_res]
    
    #combine into single df
    df_low = pd.concat(low_qs, ignore_index=True)
    df_high = pd.concat(high_qs, ignore_index=True)   

    #change namme of region2
    df_low.loc[~df_low.region2.isin(['71','72','73','75','77','78']),'region2'] = 'huc'+df_low['region2']
    df_low.loc[df_low.region2.isin(['71','72','73','75','77','78']),'region2'] = 'pfaf'+df_low['region2']
    df_high.loc[~df_high.region2.isin(['71','72','73','75','77','78']),'region2'] = 'huc'+df_high['region2']
    df_high.loc[df_high.region2.isin(['71','72','73','75','77','78']),'region2'] = 'pfaf'+df_high['region2']

    #save
    df_low.to_csv(save_path+reg_sel+'_7q10min.csv',index=False)
    df_high.to_csv(save_path+reg_sel+'_5q10max.csv',index=False)
 