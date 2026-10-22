#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT - VIC Calibration Data Creation
#STEP 3f (annual to monthly disaggregation)
#This script uses the predicted ANNUAL time series and disaggregates it based
#on the monthly index derived from the GRFR runoff
#available.
library(dplyr)
library(lubridate)
library(sf)
library(hydroGOF)
library(ggplot2)
library(vip)
library(ranger)
library(arrow)
#-----------------------------
#---FUNCTIONS
#-----------------------------
calc_monthly_runoff_percent_by_huc <- function(data, date_col, runoff_col, huc_col) {
  # Convert column names to symbols for dplyr
  date_sym <- rlang::sym(date_col)
  runoff_sym <- rlang::sym(runoff_col)
  huc_sym <- rlang::sym(huc_col)
  
  # Extract year and month from date
  result <- data %>%
    dplyr::mutate(
      Year = lubridate::year(!!date_sym),
      month = lubridate::month(!!date_sym)
    ) %>%
    # Calculate monthly totals by HUC
    dplyr::group_by(!!huc_sym, Year, month) %>%
    dplyr::summarise(
      monthly_runoff = sum(!!runoff_sym, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    # Calculate annual totals and percentages by HUC
    dplyr::group_by(!!huc_sym, Year) %>%
    dplyr::mutate(
      annual_runoff = sum(monthly_runoff, na.rm = TRUE),
      percent_of_annual = round((monthly_runoff / annual_runoff) * 100, 2)
    ) %>%
    dplyr::ungroup() %>%
    dplyr::arrange(!!huc_sym, Year, month)
  
  return(result)
}

disaggregate_annual_to_monthly <- function(monthly_percent_df, annual_df, 
                                           huc_col, 
                                           year_col,
                                           annual_value_col) {
  # Standardize column names for joining
  annual_df_renamed <- annual_df %>%
    rename(
      HUC = !!rlang::sym(huc_col),
      Year = !!rlang::sym(year_col)
    )
  
  # Join and calculate monthly values
  result <- monthly_percent_df %>%
    left_join(
      annual_df_renamed,
      by = c("HUC", "Year")
    ) %>%
    mutate(
      prediction_USGS_monthly = round(
        (percent_of_annual / 100) * !!rlang::sym(annual_value_col),4)
    ) %>%
    arrange(HUC, Year, month)
  
  return(result)
}

#################################
#---Main code-------------------
#################################
mainPath="/Users/giov232/Documents/Research Topics/FORESIGHT/"
centerVal=1

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/summary/final models/disaggregated/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

hucsToUse=c("01","02","03","04","08","09","10","12","13","17","18")
for (h in hucsToUse){
  huc02_val=h
  ################################################################################
  #---Read in the predicted USGS quick flow file from RF model output
  pr.files=list.files(paste0(mainPath,"Data/output/summary/final models/annual"),full.names = T,pattern = ".csv$")
  pr.files_flag=file.exists(pr.files[grep(paste0("predicted_USGS_HUC",huc02_val,"_",centerVal),pr.files)])
  mt.files_flag=file.exists(pr.files[grep(paste0("model_timeseries_RF_HUC_",huc02_val,"_",centerVal,".csv$"),pr.files)])
  if(pr.files_flag & mt.files_flag){
    pr.files_sub=pr.files[grep(paste0("predicted_USGS_HUC",huc02_val,"_",centerVal),pr.files)]
    pr=read.csv(pr.files_sub,header = T)
    mt.files_sub=pr.files[grep(paste0("model_timeseries_RF_HUC_",huc02_val,"_",centerVal,".csv$"),pr.files)]
    mt=read.csv(mt.files_sub,header = T)
    colnames(mt)=c("HUC","clusterVal","Year","observed_USGS","predictions_USGS","GRFR")
  }else{
    pr.files_sub=pr.files[grep(paste0("model_timeseries_RF_HUC_",huc02_val,"_",centerVal),pr.files)]
    pr=read.csv(pr.files_sub,header = T)
    colnames(pr)=c("HUC","clusterVal","Year","observed_USGS","predictions_USGS","GRFR")
  }
  ################################################################################
  #---Read in GRFR runoff csv file (spatial average values)
  gr.files=list.files(paste0(mainPath,"Data/output/monthly"),full.names = T,pattern = ".parquet$")
  gr.files_sub=gr.files[grep(paste0("GRFR_HUC_",huc02_val,"_monthly.parquet"),gr.files)]
  gr=read_parquet(gr.files_sub,header = T)
  gr=na.omit(gr)
  gr$Date=as.POSIXct(gr$Date,"%Y-%m-%d",tz="GMT")
  gr=gr[,names(gr) %in% c("HUC","runoff_month_sum","Date")]
  gr$Dataset="GRFR"
  gr$Year=year(gr$Date)
  gr$HUC=as.numeric(gr$HUC)
  
  #Create shaping index using GRFR monthly runoff values (proportional shaping)
  monthly_percents=calc_monthly_runoff_percent_by_huc(gr,"Date","runoff_month_sum","HUC")
  
  #Create the disaggregated USGS QF values using the annual USGS runoff and GRFR shape
  if(pr.files_flag & mt.files_flag){#HUCs where transfer function is applied for annual volumes
    #Predicted values
    prediction_USGS=pr[!names(pr) %in% c("clusterVal","GRFR")]
    usgs_mon_pred=disaggregate_annual_to_monthly(monthly_percents,prediction_USGS,"HUC","Year","predictions_USGS")
    usgs_mon_pred$Date=as.POSIXct(paste0(usgs_mon_pred$Year,"-",usgs_mon_pred$month,"-01"),"%Y-%m-%d",tz="GMT")
    usgs_mon_pred=na.omit(usgs_mon_pred)
    #usgs_mon_pred=usgs_mon_pred %>% filter(HUC %in% huc_final_list$HUC)
    #Disaggregation of USGS runoff
    existing_USGS=mt[!names(mt) %in% c("clusterVal","GRFR","predictions_USGS")]
    usgs_mon_dis=disaggregate_annual_to_monthly(monthly_percents,existing_USGS,"HUC","Year","observed_USGS")
    usgs_mon_dis$Date=as.POSIXct(paste0(usgs_mon_dis$Year,"-",usgs_mon_dis$month,"-01"),"%Y-%m-%d",tz="GMT")
    usgs_mon_dis=na.omit(usgs_mon_dis)
  }else{#HUCs where only monthly shaping is occurring
    existing_USGS=pr[!names(pr) %in% c("clusterVal","GRFR","predictions_USGS")]
    usgs_mon_dis=disaggregate_annual_to_monthly(monthly_percents,existing_USGS,"HUC","Year","observed_USGS")
    usgs_mon_dis$Date=as.POSIXct(paste0(usgs_mon_dis$Year,"-",usgs_mon_dis$month,"-01"),"%Y-%m-%d",tz="GMT")
    usgs_mon_dis=na.omit(usgs_mon_dis)
  }

  #Alter file name based on whether the basins are all in CONUS or not
  if(pr.files_flag & mt.files_flag){
    filename_pred=paste0(mainPath,"Data/output/summary/final models/disaggregated/predicted_USGS_HUC",huc02_val,"_",centerVal,"_TFoutput.csv")
    filename_dis=paste0(mainPath,"Data/output/summary/final models/disaggregated/predicted_USGS_HUC",huc02_val,"_",centerVal,".csv")
    usgs_mon_pred=unique(usgs_mon_pred)
    usgs_mon_dis=unique(usgs_mon_dis)
    write.table(usgs_mon_pred, 
                file = filename_pred, 
                col.names=T, row.names = FALSE,sep = ",")
    write.table(usgs_mon_dis, 
                file = filename_dis, 
                col.names=T, row.names = FALSE,sep = ",")
  }else{
    filename_dis=paste0(mainPath,"Data/output/summary/final models/disaggregated/predicted_USGS_HUC",huc02_val,"_",centerVal,".csv")
    usgs_mon_dis=unique(usgs_mon_dis)
    write.table(usgs_mon_dis, 
                file = filename_dis, 
                col.names=T, row.names = FALSE,sep = ",")
  } #End of conditional for whether or not we are disaggregating the output for basins with no USGS QF info or not

} #End of loop through all HUCs

print(length(unique(usgs_mon_dis$HUC)))
print(length(unique(usgs_mon_pred$HUC)))
print(length(unique(usgs_mon_dis$HUC)))+print(length(unique(usgs_mon_pred$HUC)))
