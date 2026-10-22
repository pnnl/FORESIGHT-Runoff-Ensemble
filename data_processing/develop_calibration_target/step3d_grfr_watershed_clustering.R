#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT - VIC Calibration Data Creation
#STEP 3d (clustering)
#This script uses the monthly summary time series information created in the 
#R script named 'create_summary_TS_monthly.R' to find groups of
#watersheds. The goal of the script is to group watersheds using the GRFR runoff
#where there is USGS Quick Flow data with those outside of CONUS where we need 
#to create the information for calibration
library(dplyr)
library(lubridate)
library(reshape2)
library(stringr)
library(sf)
library(stats)
library(arrow)
mainPath="input_data/calibration_target/"

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/summary/clusters/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

spatialOutSwitch=0
hucsToUse=c("01","02","03","04","08","09","10","12","13","17","18") #c("01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18") #c("02","04","09","10","12","13","15","18")
for (h in hucsToUse){
  huc02_val=h
  ################################################################################
  #---Read in the USGS monthly summary file
  qf.files=list.files(paste0(mainPath,"Data/output/summary/Statistics/"),full.names = T,pattern = ".csv$")
  qf.files_sub=qf.files[grep(paste0("summary_USGS_HUC_",huc02_val),qf.files)]
  qf=read.csv(qf.files_sub,header = T)
  qf$Dataset="USGS"
  qf_hucs=qf$HUC
  ################################################################################
  #---Read in GRFR runoff csv file (spatial average values)
  gr.files=list.files(paste0(mainPath,"Data/output/summary/Statistics/"),full.names = T,pattern = ".csv$")
  gr.files_sub=gr.files[grep(paste0("summary_GRFR_HUC_",h),gr.files)]
  grAll=read.csv(gr.files_sub,header = T)
  grAll$Dataset="GRFR"
  grAll=unique(grAll)
  #grAll_hucs=grAll$HUC
  ################################################################################
  #Perform clustering by different monthly summary values
  scale_monthlyData_byHUC <- function(df,statName){
    library(reshape2)
    df$MonthName=month.abb[df$Month]
    df_sub=df[,names(df) %in% c('HUC','Month',statName)]
    df_cast=dcast(df_sub,HUC ~ Month,value.var = statName,fun.aggregate = mean)
    df_cast=scale(df_cast[,2:ncol(df_cast)],center = T,scale = T)
    return(df_cast)
  }
  
  #---KMEANS CLUSTERING-----------------------------------------------------------
  #Determine potential number of clusters
  #factoextra::fviz_nbclust(gr_mean_scaled, kmeans, method = "silhouette", k.max = 11)
  
  #Specify number of clusters
  centerVal=1
  
  #1) Mean
  gr_mean_scaled=scale_monthlyData_byHUC(grAll,'Mean')
  # Set a seed for reproducibility
  set.seed(123) 
  
  # Perform k-means clustering with a chosen number of clusters (e.g., k=4)
  k_clusters_mean <- kmeans(x = gr_mean_scaled, centers = centerVal, nstart = 25)
  
  # Add the cluster assignment back to your original dataframe
  gr.out=data.frame(HUC=unique(grAll$HUC),cluster_mean=k_clusters_mean$cluster)
  
  #2) Median
  gr_med_scaled=scale_monthlyData_byHUC(grAll,'Median')
  # Set a seed for reproducibility
  set.seed(123) 
  
  # Perform k-means clustering with a chosen number of clusters (e.g., k=4)
  k_clusters_med <- kmeans(x = gr_med_scaled, centers = centerVal, nstart = 25)
  
  # Add the cluster assignment back to your original dataframe
  gr.out$cluster_med=k_clusters_med$cluster
  
  #---HIERARCHICAL CLUSTERING-----------------------------------------------------
  #3) Mean
  # Compute the distance matrix
  distance_matrix_mean <- dist(gr_mean_scaled, method = "euclidean")
  
  # Perform hierarchical clustering
  hc_result_mean <- hclust(distance_matrix_mean, method = "complete") 
  
  # Cut the tree to get a specific number of clusters (e.g., 4)
  gr.out$cluster_hc_mean=cutree(hc_result_mean,k=centerVal)
  
  #3) Median
  # Compute the distance matrix
  distance_matrix_med <- dist(gr_med_scaled, method = "euclidean")
  
  # Perform hierarchical clustering
  hc_result_med <- hclust(distance_matrix_med, method = "complete") 
  
  # Cut the tree to get a specific number of clusters (e.g., 4)
  gr.out$cluster_hc_med=cutree(hc_result_med, k=centerVal)
  
  #Add correlation results to spatial object for visualizing
  if(spatialOutSwitch==1){
    #Get polygon file being used for VIC development
    spFile.list=list.files(paste0(mainPath,"/Data/GIS"),".gpkg$", full.names = T)
    spFileName=spFile.list[grep(paste0("conus_HUC12_merit"),spFile.list)] #file should be same as used for VIC development
    watershed_polygons=read_sf(dsn = spFileName)
    watershed_polygons$HUC02=str_sub(watershed_polygons$HUCIDX,1,2)
    watershed_polygons_sub=watershed_polygons[as.numeric(watershed_polygons$HUCIDX) %in% qf_hucs,]
    
    #Add clustering results to geospatial file for visualization on map
    #NOTE: hierarchical clustering results not added to output since they were not informative compared to kmeans
    cluster_to_add_to_spFile=data.frame(HUCIDX=as.character(gr.out$HUC),kmeans_mean=gr.out$cluster_mean,kmeans_med=gr.out$cluster_med)
    watershed_polygons_cluster=dplyr::left_join(watershed_polygons_sub,cluster_to_add_to_spFile,by="HUCIDX")
    st_write(watershed_polygons_cluster, paste0(mainPath,"Data/output/summary/spatial files/cluster_HUC",huc02_val,"_centers_",centerVal,".gpkg"))
  }
  write.csv(gr.out,file=paste0(mainPath,"Data/output/summary/clusters/cluster_by_HUC02_",huc02_val,"_centers_",centerVal,".csv"),row.names = F)
}
