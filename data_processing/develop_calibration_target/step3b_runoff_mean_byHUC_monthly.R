#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT - VIC Calibration Data Creation
#STEP 3b (GRFR)
#This script creates monthly total runoff values for the GRFR dataset.
#The monthly values are summed from the daily data files that were produced 
#by the 'runoff_mean_byHUC_parallel.R' script
################################################################################
library(terra)
library(dplyr)
library(lubridate)
library(data.table)
library(arrow)
mainPath="input_data/calibration_target/"

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/monthly/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

hucsToUse=c("01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18")
for (h in hucsToUse){
  huc02_val=h
  #---Read in GRFR runoff csv file (spatial average values)
  gr.files=list.files(paste0(mainPath,"Data/output/daily/"),full.names = T,pattern = ".parquet$")
  gr=gr.files[grep(paste0("HUC_",huc02_val,"_final.parquet"),gr.files)]
  gdf=read_parquet(gr)
  gdf$Year=year(gdf$Date)
  gdf$Month_val=month(gdf$Date)
  
  #Sum to total monthly runoff
  gdf_m=gdf %>%
    group_by(HUC,Year,Month_val) %>%
    summarize(runoff_month_sum=sum(as.numeric(weighted_mean_runoff),na.rm=T))
  
  gdf_m$Date=as.POSIXct(paste0(gdf_m$Year,"-",gdf_m$Month_val,"-01"),"%Y-%m-%d",tz="GMT")
  
  #Output monthly data to file for use in other analysis
  write_parquet(gdf_m,sink=paste0(mainPath,"Data/output/monthly/GRFR_HUC_",huc02_val,"_monthly.parquet"))
}
