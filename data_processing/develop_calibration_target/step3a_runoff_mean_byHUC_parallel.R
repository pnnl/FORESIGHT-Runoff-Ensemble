#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT - VIC Calibration Data Creation
#STEP 3a (parallel)
#This script creates the spatial average runoff values from the GRFR dataset based on the HUC polygons
#that are being used for the VIC model calibration. This information will be used to develop a 'transfer' 
#function to compare with the USGS quick flow data so we can calibrate for areas outside of CONUS that
#will be included in the hydrology model development.
#
#NOTE: this script processes the spatial averages in PARALLEL (takes about 1/3 time as serial)
#####################################################################################################
library(terra)
library(sf)
library(stringr)
library(doParallel)
library(foreach)
library(parallel)
library(exactextractr)
library(pbapply)
library(arrow)
library(dplyr)
mainPath="input_data/calibration_target"

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

#Get list of files for processing
nc.list=list.files(paste0(mainPath,"/Data/runoff/grfr/"),".nc$", full.names = T)
nc.names=list.files(paste0(mainPath,"/Data/runoff/grfr/"),".nc$")

#Subset watersheds by different HUC or areas outside of CONUS
huc_subset_names="18" #Should be HUC02 code (run HUC at a time for QC purposes)

#Output Options
outputDailyMean=FALSE

ptm <- Sys.time()
#Using CONUS watershed file - remember to change HUC02 numbers!
spFile.list=list.files(paste0(mainPath,"/Data/GIS/TF_geospatial_files_byhuc2"),".shp$", full.names = T)

spFileName=spFile.list[grep(paste0(huc_subset_names),spFile.list)]
watershed_polygons=read_sf(dsn = spFileName)
watershed_hucs=watershed_polygons$HUCIDX
numPolygons=nrow(watershed_polygons)

#-------------------------------------------------
# Run sequentially to find which polygon(s) fail
# Check to see if any geometries will cause an issue
#------------------------------------------------
failed <- c()
rt_test=rast(nc.list[1])
for (p in 1:numPolygons) {
  huc <- watershed_hucs[p]
  wp <- watershed_polygons[watershed_polygons$HUCIDX == huc, ]
  wp <- st_transform(wp, st_crs(rt_test))
  
  result <- tryCatch(
    exact_extract(rt_test, wp, fun = 'mean'),
    error = function(e) {
      cat("FAILED at polygon", p, "(HUC:", huc, ") -", e$message, "\n")
      return(NULL)
    }
  )
  if (is.null(result)) failed <- c(failed, p)
}

cat("\nTotal failed:", length(failed), "out of", numPolygons, "\n")

#-------------------------------------------------
# Loop through all years we have the GRFR data
# skip all hucs that have issues with the geometry
#-------------------------------------------------
for (y in 1:length(nc.list)){
  #read in GRFR raster for runoff values
  rt=rast(nc.list[y])
  yr=str_split_fixed(str_split_fixed(nc.names[y],"_",5)[5],".nc",2)[1]
  
  # Get time information
  time_vals <- terra::time(rt)
  
  # Filter by geometry that is ok
  if (!is.null(failed) && length(failed) > 0) {
    watershed_polygons <- watershed_polygons %>% dplyr::slice(-failed)
  }
  watershed_hucs=watershed_polygons$HUCIDX
  
  #Create the weighted mean runoff for each huc
  watershed_polygons <- st_transform(watershed_polygons, st_crs(rt))
  st_make_valid(watershed_polygons)
  results <- exact_extract(rt, watershed_polygons, fun = 'mean')
  out_weightedMean <- results
  out_weightedMean$HUC <- watershed_hucs

  # Rename columns and arrange for output
  colnames(out_weightedMean) <- c(as.character(time_vals),"HUC")
  out_weightedMean=reshape2::melt(out_weightedMean,id.vars=c("HUC"))
  colnames(out_weightedMean)=c("HUC","GRFR_date","weighted_mean_runoff")
  out_weightedMean$Date=as.POSIXct(as.character(out_weightedMean$GRFR_date),"%Y-%m-%d",tz="GMT")
  out_weightedMean=out_weightedMean[order(out_weightedMean$HUC),]
  
  #Option to output daily values
  if(outputDailyMean){
    write_parquet(out_weightedMean,file = paste0(mainPath,"Data/output/daily/weighted_mean_",huc_subset_names,"_",yr,".parquet"))
  }
  
  #Write out data to single file that will have all watersheds and years
  write_header <- !file.exists(paste0(mainPath,"Data/output/HUC_",huc_subset_names,"_allYears2.csv"))
  write.table(out_weightedMean,file = paste0(mainPath,"Data/output/HUC_",huc_subset_names,"_allYears2.csv"),
              row.names = F,append = !write_header,sep = ",",col.names=write_header)
} #End of loop through all years

# Calculate the elapsed time
print(Sys.time() - ptm)

#Convert file to parquet file
open_dataset(paste0(mainPath,"Data/output/HUC_",huc_subset_names,"_allYears2.csv"), format = "csv") |>
  write_dataset(paste0(mainPath,"Data/output/"), format = "parquet")

