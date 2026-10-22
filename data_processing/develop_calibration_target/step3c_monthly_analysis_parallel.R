#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT - VIC Calibration Data Creation
#STEP 3c (parallel-all months)
#This script uses the monthly time series values to calculated correlation statistics
#NOTE: this code uses parallel processing
library(terra)
library(dplyr)
library(lubridate)
library(sf)
library(parallel)
library(pbapply)
library(hydroGOF)
library(arrow)
mainPath="input_data/calibration_target"
spatialOutSwitch=0

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/summary/Statistics/metrics/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

hucsToUse=c("01","02","03","04","08","09","10","12","13","17","18") #c("01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18")
for (h in hucsToUse){
  huc02_val=h
  ################################################################################
  #---Read in the USGS quick flow file
  qf.files=list.files(paste0(mainPath,"Data/output/monthly/"),full.names = T,pattern = ".parquet$")
  qf=read_parquet(qf.files[grep(paste0("USGS_HUC_",huc02_val),qf.files)])
  qf$Date=as.POSIXct(qf$Date,"%Y-%m-%d",tz="GMT")
  qf$Dataset="USGS"
  ################################################################################
  #---Read in GRFR runoff csv file (spatial average values)
  gr.files=list.files(paste0(mainPath,"Data/output/monthly"),full.names = T,pattern = ".parquet$")
  gr.files_sub=gr.files[grep(paste0("GRFR_HUC_",huc02_val,"_monthly.parquet"),gr.files)]
  gr=read_parquet(gr.files_sub)
  gr=na.omit(gr)
  gr$HUC=dataRetrieval::zeroPad(as.character(gr$HUC),12)
  gr$Date=as.POSIXct(gr$Date,"%Y-%m-%d",tz="GMT")
  gr=gr[,names(gr) %in% c("HUC","runoff_month_sum","Date")]
  gr$Dataset="GRFR"
  ################################################################################
  #---Perform analysis both the USGS QF and GRFR monthly runoff data frames
  #Get min/max dates that are common for both datasets
  minDate=max(min(qf$Date),min(gr$Date))
  maxDate=min(max(qf$Date),max(gr$Date))
  
  hucs=data.frame(unique(qf$HUC))
  num.basins=nrow(hucs)
  
  # Determine the number of cores to use
  num_cores <- detectCores() - 10  # Leave more than one core due to forking issue with Mac (never had this issue with Windows machine)
  
  # Set up cluster
  cl <- makeCluster(num_cores)
  
  # Export necessary variables to all cores
  clusterExport(cl, c("gr", "qf", "hucs", "minDate", "maxDate"))
  
  # Load hydroGOF on all cores
  clusterEvalQ(cl, library(hydroGOF))
  
  # Parallel processing with progress bar
  corAll <- pblapply(1:num.basins, function(b) {
    tryCatch(
      {
        # Subset data for specific HUC and date range for groundwater record
        gf_subset <- gr[gr$HUC == hucs[b,] & minDate <= gr$Date & gr$Date <= maxDate, ]
        
        # Subset data for specific HUC and date range for runoff record
        qf_subset <- qf[qf$HUC == hucs[b,] & minDate <= qf$Date & qf$Date <= maxDate, ]
        
        # Calculate Pearson correlation
        out <- data.frame(
          HUC = hucs[b,],
          gr_row=nrow(gf_subset),
          qf_row=nrow(qf_subset),
          Pearson_r = cor(qf_subset$runoff_month_sum, gf_subset$runoff_month_sum, method = 'pearson'),
          nseVal=NSE(qf_subset$runoff_month_sum,gf_subset$runoff_month_sum),
          kgeVal=KGE(qf_subset$runoff_month_sum,gf_subset$runoff_month_sum,method = '2009')
        )
        return(out)
      },
      error=function(e){
        out <- data.frame(
          HUC = hucs[b,],
          gr_row=nrow(gf_subset),
          qf_row=nrow(qf_subset),
          Pearson_r = NA,
          nseVal = NA,
          kgeVal = NA
        )
      }) #End of try/catch
  }, cl = cl) #end of pbapply function
  
  # Stop the cluster
  stopCluster(cl)
  
  # Combine results
  corAll <- data.table::rbindlist(corAll)
  rows_not_equal_baseR <- corAll[corAll$gr_row != corAll$qf_row, ]
  write.csv(corAll,paste0(mainPath,"Data/output/summary/Statistics/metrics/metrics_HUC_",huc02_val,".csv"),row.names = F)
  
  #Add correlation results to spatial object for visualizing
  if(spatialOutSwitch==1){
    #Check that output directory exists
    dir_path=paste0(mainPath,"Data/output/summary/spatial files/")
    if (!dir.exists(dir_path)) {
      dir.create(dir_path, recursive = TRUE)
    }
    #Create and write out spatial file--Assumes the basins geometry are already processes 
    spFile.list=list.files(paste0(mainPath,"/Data/GIS/HUC12_basins"),".shp$", full.names = T)
    spFileName=spFile.list[grep(paste0("HUC",huc_subset_names,"_merit"),spFile.list)]
    watershed_polygons=read_sf(dsn = spFileName)
    corr_to_add_to_spFile=data.frame(HUC12=as.character(corAll$HUC),Pearson_r=corAll$Pearson_r,NSE=corAll$nseVal,KGE=corAll$kgeVal)
    watershed_polygons_corr=dplyr::left_join(watershed_polygons,corr_to_add_to_spFile,by="HUC12")
    st_write(watershed_polygons_corr, paste0(mainPath,"Data/output/summary/spatial files/metrics_HUC",huc02_val,".shp"))
  }
}
##################################################################################

