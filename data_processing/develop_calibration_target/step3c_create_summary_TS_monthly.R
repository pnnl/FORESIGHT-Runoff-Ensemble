#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT - VIC Calibration Data Creation
#STEP 3c (Summary Statistics)
#This script uses the monthly time series to calculated summary statistics
#which can then be used to find watersheds that are similar. The similar
#watersheds will be evaluated first when building the transfer function between the 
#GRFR and USGS QF datasets in basins outside of CONUS.
library(dplyr)
library(lubridate)
library(sf)
library(parallel)
library(pbapply)
library(hydroGOF)
library(arrow)
mainPath="input_data/calibration_target/"

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/summary/Statistics/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

dataSwitch="Both"
hucsToUse=c("01","02","03","04","08","09","10","12","13","17","18") #c("01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18") #c("01","02","04","09","10","12","13","15","18")
for (h in hucsToUse){
  huc02_val=h
################################################################################
#---Read in the USGS quick flow file
  if(dataSwitch=="Both" | dataSwitch=="USGS"){
    qf.files=list.files(paste0(mainPath,"Data/output/monthly/"),full.names = T,pattern = ".parquet$")
    qf.files_sub=qf.files[grep(paste0("USGS_HUC_",huc02_val),qf.files)]
    qf=read_parquet(qf.files_sub)
    qf$Date=as.POSIXct(qf$Date,"%Y-%m-%d",tz="GMT")
    qf$Dataset="USGS"
    qf$Month=month(qf$Date)
  }
################################################################################
  #---Read in GRFR runoff csv file (spatial average values)
  if(dataSwitch=="Both" | dataSwitch=="GRFR"){
    gr.files=list.files(paste0(mainPath,"Data/output/monthly"),full.names = T,pattern = ".parquet$")
    gr.files_sub=gr.files[grep(paste0("GRFR_HUC_",huc02_val,"_monthly.parquet"),gr.files)]
    gr=read_parquet(gr.files_sub)
    gr=na.omit(gr)
    gr$Date=as.POSIXct(gr$Date,"%Y-%m-%d",tz="GMT")
    gr=gr[,names(gr) %in% c("HUC","runoff_month_sum","Date")]
    gr$Dataset="GRFR"
    gr$Month=month(gr$Date)
  }
################################################################################
  #Filter date range if we have both GRFR and USGS data to make sure they align
  if(dataSwitch=="Both"){
    #Get min/max dates that are common for both datasets
    minDate=max(min(qf$Date),min(gr$Date))
    maxDate=min(max(qf$Date),max(gr$Date))
    #Subset the data by min/max dates both are available
    gr_sub=gr[minDate<=gr$Date & gr$Date<=maxDate,] #limit dates first by USGS QF POR
    qf_sub=qf[minDate<=qf$Date & qf$Date<=maxDate,] #limit dates next by the GRFR POR
  }else{
    gr_sub=gr
    qf_sub=qf
  }
  #USGS QF Data
  if(dataSwitch=="Both" | dataSwitch=="USGS"){
    qf.mon=qf_sub %>%
            group_by(HUC,Month) %>%
            summarise(Mean=mean(runoff_month_sum),
                      Median=median(runoff_month_sum),
                      P10=quantile(runoff_month_sum,0.1),
                      P25=quantile(runoff_month_sum,0.25),
                      P75=quantile(runoff_month_sum,0.75),
                      P90=quantile(runoff_month_sum,0.9))
    write.csv(qf.mon,file=paste0(mainPath,"Data/output/summary/Statistics/summary_USGS_HUC_",huc02_val,".csv"),row.names = F)
  }
  #GRFR Data
  if(dataSwitch=="Both" | dataSwitch=="GRFR"){
    gr.mon=gr_sub %>%
      group_by(HUC,Month) %>%
      summarise(Mean=mean(runoff_month_sum),
                Median=median(runoff_month_sum),
                P10=quantile(runoff_month_sum,0.1),
                P25=quantile(runoff_month_sum,0.25),
                P75=quantile(runoff_month_sum,0.75),
                P90=quantile(runoff_month_sum,0.9))
    
    write.csv(gr.mon,file=paste0(mainPath,"Data/output/summary/Statistics/summary_GRFR_HUC_",huc02_val,".csv"),row.names = F)
  }
}