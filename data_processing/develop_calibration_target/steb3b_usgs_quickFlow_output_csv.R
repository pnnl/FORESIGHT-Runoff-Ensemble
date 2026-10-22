#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT
#STEP 3b (USGS QF)
#This script creates a summary data file for monthly runoff values from the USGS Quick Flow
#with the monthly dates aligned with the runoff
##########################################################################################
library(terra)
library(dplyr)
library(lubridate)
library(ncdf4)
library(parallel)
library(pbapply)
library(arrow)

mainPath="input_data/calibration_target/"

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

hucsToUse=c("01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18")
for (h in hucsToUse){
  huc02_val=h
  
  #---Read in the USGS quick flow file
  qf.files=list.files(paste0(mainPath,"Data/runoff/usgs_qf"),full.names = T,pattern = ".nc$")
  qf=qf.files[grep(paste0("huc",huc02_val),qf.files)]
  
  #Open netcdf file
  nc=nc_open(qf)
  
  #Get variables from netcdf file
  #Basin ID
  basin=data.frame(ncvar_get(nc,"basin"))
  num.basins=nrow(basin)
  
  #Time step
  origin_date <- "1975-01-01"
  time_vals_raw=ncvar_get(nc,"time")
  dates=as.Date(time_vals_raw,origin=origin_date,tz="GMT","%Y-%m-%d")
  
  #Cumulative monthly runoff values
  roff=ncvar_get(nc,"runoff_mm")
  
  #Close netcdf file
  nc_close(nc)
  
  #---Create formattedd table from the netcdf file information for easier data analysis
  # Determine the number of cores to use
  num_cores <- detectCores() - 10  # Leave more than one core due to forking issue with Mac (never had this issue with Windows machine)
  
  # Set up cluster
  cl <- makeCluster(num_cores)
  
  # Export necessary variables to all cores
  clusterExport(cl, c("basin", "dates", "roff"))
  
  # Parallel processing with progress bar
  outAll <- pblapply(1:num.basins, function(b) {
    qf <- data.frame(
      HUC = basin[b,],
      Date = dates,
      runoff_month_sum = roff[b,]
    )
    return(qf)
  }, cl = cl)
  
  # Stop the cluster
  stopCluster(cl)
  
  # Combine results
  outAll <- data.table::rbindlist(outAll)
  
  #Output monthly data to file for use in other analysis
  write_parquet(outAll,sink = paste0(mainPath,"Data/output/monthly/USGS_HUC_",huc02_val,"_monthly.parquet"))
}