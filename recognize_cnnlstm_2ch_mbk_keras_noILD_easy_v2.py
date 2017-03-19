
import sys
#sys.path.append('/user/HS103/yx0001/Downloads/Hat')
import pickle
import numpy as np
np.random.seed(1515)
import scipy.stats

import keras
from keras.models import load_model

from keras import backend as K

import config_2ch_raw_mbk_ipld_eva as cfg
import prepare_data_2ch_raw_ipd_ild_easy as pp_data
import csv
from preprocessing import reshape_3d_to_4d
from keras.layers import Merge, Input, merge
from preprocessing import sparse_to_categorical, mat_2d_to_3d
from preprocessing import sparse_to_categorical, mat_2d_to_3d, reshape_3d_to_4d
from metrics import prec_recall_fvalue
import cPickle
import eer
import matplotlib.pyplot as plt
#from main_cnn import fe_fd, agg_num, hop, n_hid, fold
np.set_printoptions(threshold=np.nan, linewidth=1000, precision=2, suppress=True)


# resize data for fit into CNN. size: (batch_num*color_maps*height*weight)
def reshapeX( X ):
    N = len(X)
    return X.reshape( (N, 6, t_delay, feadim, 1) )

# resize data for fit into CNN. size: (batch_num*color_maps*height*weight)
def reshapeX2( X ):
    N = len(X)
    return X.reshape( (N, t_delay, feadim) )

def reshapeX1( X ):
    N = len(X)
    return X.reshape( (N, t_delay, 1, feadim, 1) )

def outfunc(vects):
    x,y=vects
    #y=K.sum( y, axis=1 )
    y = K.clip( y, 1.0e-9, 1 )     # clip to avoid numerical underflow
    #z=Lambda(lambda x: K.sum(x, axis=1),output_shape=(8,))(y)
    y = K.sum(y, axis=1)
    #z = RepeatVector(249)(z)
    #z=Permute((2,1))(z)
    #return K.sum( x / z, axis=1 )
    return K.sum( x, axis=1 ) / y

def myloss(detv2):
    result_bc=myloss_bc(y_true,y_pred,detv2)
    return result_bc

def myloss_bc(y_true,y_pred,detv2):
    y_pred=K.switch(y_true < 0.1 ,y_pred*detv2/249,y_pred)
    return K.mean(K.binary_crossentropy(y_pred,y_true),axis=-1)

def reshapeX3( X ):
    N = len(X)
    return X.reshape( (N, t_delay*feadim) )

feadim=40
t_delay=249


debug=1
# hyper-params
n_labels = len( cfg.labels )
fe_fd_left = cfg.dev_fe_mel_fd_left
fe_fd_right = cfg.dev_fe_mel_fd_right
fe_fd_mean = cfg.dev_fe_mel_fd_mean
fe_fd_diff = cfg.dev_fe_mel_fd_diff
fe_fd_ipd = cfg.dev_fe_mel_fd_ipd
fe_fd_ild = cfg.dev_fe_mel_fd_ild
#fe_fd_ori = cfg.dev_fe_mel_fd_ori
agg_num = t_delay        # concatenate frames
hop = t_delay         # step_len
n_hid = 1000
fold = 1 # can be 0, 1, 2, 3

# load model
# load model
#md = serializations.load( cfg.scrap_fd + '/Md/md20.p' )
#md=load_model('/vol/vssp/msos/yx/chime_home/DCASE2016_task4_scrap_2ch_mbk_ipd_ild_overlap/Md/ONLYdetection_softmaxdiv_clip_utt_keras_overlap50_eva816_1CNN128onMBK40_noILD_weights.20-0.19.hdf5') ### best!
#md=load_model('/vol/vssp/msos/yx/chime_home/DCASE2016_task4_scrap_2ch_mbk_ipd_ild_overlap/Md/attention_detection_clipV2_utt_keras_overlap50_eva816_1CNN128onMBK40_noILD_weights.20-0.21.hdf5')### better!
#md=load_model('/vol/vssp/msos/yx/chime_home/DCASE2016_task4_scrap_2ch_mbk_ipd_ild_overlap/Md/Attention_detection_clip_Mult3V2_utt_keras_overlap50_eva816_1CNN128onMBK40_noILD_weights.16-0.20.hdf5') ### best!!!
#md=load_model('/vol/vssp/msos/yx/chime_home/DCASE2016_task4_scrap_2ch_mbk_ipd_ild_overlap/Md/ONLYdetectionImpr_softmaxdiv_clip_utt_keras_overlap50_eva816_1CNN128onMBK40_noILD_weights.07-0.01.hdf5',custom_objects={'myloss_bc':myloss_bc}) 

#md=load_model('/vol/vssp/msos/yx/chime_home/DCASE2016_task4_scrap_2ch_mbk_ipd_ild_overlap/best-eval-model/Attention_detection_clipV2_utt_keras_overlap50_eva816_1CNN128onMBK40_noILD_weights.05-0.27.hdf5-Detectiongood-on-fold1-3rd-notGoodonFold9') 


#md.summary()

def recognize():
    ## prepare data
    #_, _, te_X, te_y = pp_data.GetAllData(fe_fd_right, fe_fd_left, fe_fd_mean, fe_fd_diff, agg_num, hop, fold )
    ##te_X = reshapeX(te_X)
    #print te_X.shape
    
    # do recognize and evaluation
    thres = 0.4     # thres, tune to prec=recall, if smaller, make prec smaller
    n_labels = len( cfg.labels )
    
    gt_roll = []
    pred_roll = []
    result_roll = []
    y_true_binary_c = []
    y_true_file_c = []
    y_true_binary_m = []
    y_true_file_m = []
    y_true_binary_f = []
    y_true_file_f = []
    y_true_binary_v = []
    y_true_file_v = []
    y_true_binary_p = []
    y_true_file_p = []
    y_true_binary_b = []
    y_true_file_b = []
    y_true_binary_o = []
    y_true_file_o = []
    with open( cfg.dev_cv_csv_path, 'rb') as f:
        reader = csv.reader(f)
        lis = list(reader)
        
        line_n=0
        # read one line
        for li in lis:
            na = li[1]
            curr_fold = int(li[2])
            
            if fold==curr_fold:
                line_n=line_n+1
                # get features, tags
                fe_path_left = fe_fd_left + '/' + na + '.f'
                fe_path_right = fe_fd_right + '/' + na + '.f'
                fe_path_mean = fe_fd_mean + '/' + na + '.f'
                fe_path_diff = fe_fd_diff + '/' + na + '.f'
                fe_path_ipd = fe_fd_ipd + '/' + na + '.f'
                fe_path_ild = fe_fd_ild + '/' + na + '.f'
                #fe_path_ori = fe_fd_ori + '/' + na + '.f'
                info_path = cfg.dev_wav_fd + '/' + na + '.csv'
                #print na
                tags = pp_data.GetTags( info_path )
                print tags
                y = pp_data.TagsToCategory( tags )
                #print y
                #sys.exit()
                #X_l = cPickle.load( open( fe_path_left, 'rb' ) )
                #X_r = cPickle.load( open( fe_path_right, 'rb' ) )
                #X_m = cPickle.load( open( fe_path_mean, 'rb' ) )
                X_m = cPickle.load( open( '/vol/vssp/msos/yx/chime_home/DCASE2016_task4_scrap_2ch_spec_ipd_ild_overlap/Fe/Mel_m/CR_lounge_220110_0731.s0_chunk70.f', 'rb' ) )
                if   debug:  ### for fbank
                    # with a Sequential model
                    #md.summary()
                    print na
                    if line_n==3:
                        #layer_output=np.mean(layer_output[:,:],axis=1)
                        #layer_output=layer_output[0,:,7]
                        #imgplot1,=plt.plot(X_m) 
                        #print     layer_output             
                        #imgplot=plt.matshow(np.rot90(X_m))
                        imgplot=plt.imshow(20*np.log10(abs(X_m.T)), origin='lower', aspect='auto')
                        #imgplot.set_cmap('spectral')
                        #plt.colorbar()
                        plt.xlabel('Frame number')
                        plt.ylabel('Frequency')
                        plt.show()
                        sys.pause()
                continue
                #print X_m.shape
                #X_d = cPickle.load( open( fe_path_diff, 'rb' ) )
                #X_ipd = cPickle.load( open( fe_path_ipd, 'rb' ) )
                #X_ild = cPickle.load( open( fe_path_ild, 'rb' ) )
                #X_o = cPickle.load( open( fe_path_ori, 'rb' ) )

                # aggregate data
                #X3d_l = mat_2d_to_3d( X_l, agg_num, hop )
                #X3d_r = mat_2d_to_3d( X_r, agg_num, hop )
                X3d_m = mat_2d_to_3d( X_m, agg_num, hop )
   		#X3d_d = mat_2d_to_3d( X_d, agg_num, hop )
                #X3d_ipd = mat_2d_to_3d( X_ipd, agg_num, hop )
   		#X3d_ild = mat_2d_to_3d( X_ild, agg_num, hop )
   		#X3d_o = mat_2d_to_3d( X_o, agg_num, hop )
     	        ## reshape 3d to 4d
       	        #X4d_l = reshape_3d_to_4d( X3d_l)
                #X4d_r = reshape_3d_to_4d( X3d_r)
                #X4d_m = reshape_3d_to_4d( X3d_m)
                #X4d_d = reshape_3d_to_4d( X3d_d)
                # concatenate
                #X4d=mat_concate_multiinmaps6in(X3d_l, X3d_r, X3d_m, X3d_d, X3d_ipd, X3d_ild)
                X3d_m=reshapeX1(X3d_m)
                #X4d=np.swapaxes(X4d,1,2) # or np.transpose(x,(1,0,2))  1,0,2 is axis
                te_X1=X3d_m
                #te_X2=X3d_ild
                #te_X1 = reshapeX1(te_X1)
                #te_X2 = reshapeX2(te_X2)
                
                if not  debug: ### for localization
                    # with a Sequential model
                    #md.summary()
                    print na
                    get_3rd_layer_output = K.function([md.layers[0].input, K.learning_phase()], [md.layers[20].output])
                    layer_output = get_3rd_layer_output([te_X1, 0])[0]
                    print layer_output.shape
                    #layer_output1=layer_output[:,:]
                    if line_n==3:
                        #layer_output=np.mean(layer_output[:,:],axis=1)
                        #layer_output=layer_output[0,:,7]
                        imgplot1,=plt.plot(layer_output[0,:,0],label='c',linewidth=4) 
                        #plt.legend(handles=[imgplot1])
                        plt.hold(True)
                        imgplot2,=plt.plot(layer_output[0,:,1],label='m',linewidth=2,linestyle='--') #,linewidth=4
                        plt.hold(True)
                        imgplot3,=plt.plot(layer_output[0,:,2],label='f') #,linewidth=4
                        plt.hold(True)
                        imgplot4,=plt.plot(layer_output[0,:,3],label='v',linestyle='--') #,linewidth=4
                        plt.hold(True)
                        imgplot5,=plt.plot(layer_output[0,:,4],label='p',linewidth=2,linestyle='--') #,linewidth=4
                        plt.hold(True)
                        imgplot6,=plt.plot(layer_output[0,:,5],label='b',linestyle='--') #,linewidth=4
                        plt.hold(True)
                        imgplot7,=plt.plot(layer_output[0,:,6],label='o',linestyle='--') #,linewidth=4
                        #plt.hold(True)
                        #imgplot8,=plt.plot(layer_output[0,:,7],label='S',linewidth=3) #,linewidth=4
                        plt.legend(handles=[imgplot1,imgplot2,imgplot3,imgplot4,imgplot5,imgplot6,imgplot7])
                        plt.xlabel('Frame number')
                        plt.ylabel('Event presence probability')
                        #print     layer_output             
                        #imgplot=plt.matshow((layer_output1.T))
                        #imgplot.set_cmap('spectral')
                        #plt.colorbar()
                        plt.show()
                        sys.pause()

                if  not debug:  ### for attention
                    # with a Sequential model
                    #md.summary()
                    print na
                    get_3rd_layer_output = K.function([md.layers[0].input, K.learning_phase()], [md.layers[6].output])
                    layer_output = get_3rd_layer_output([te_X1, 0])[0]
                    print layer_output.shape
                    #layer_output1=layer_output[:,:]
                    if line_n==3:
                        #layer_output=np.mean(layer_output[:,:],axis=1)
                        #layer_output=layer_output[0,:,7]
                        imgplot1,=plt.plot(layer_output[0,:]) 
                        #print     layer_output             
                        #imgplot=plt.matshow((layer_output1.T))
                        #imgplot.set_cmap('spectral')
                        #plt.colorbar()
                        plt.xlabel('Frame number')
                        plt.ylabel('Attention factor')
                        plt.show()
                        sys.pause()


                
                #p_y_pred = md.predict( [te_X1,te_X2] )
                p_y_pred = md.predict( te_X1 )
                p_y_pred = np.mean( p_y_pred, axis=0 )     # shape:(n_label)
                #print p_y_pred.shape
                pred = np.zeros(n_labels)
                pred[ np.where(p_y_pred>thres) ] = 1
                ind=0
                for la in cfg.labels:
                    if la=='S':
                        break
                    elif la=='c':
                        y_true_file_c.append(na)
                        y_true_binary_c.append(y[ind])
                    elif la=='m':
                        y_true_file_m.append(na)
                        y_true_binary_m.append(y[ind])
                    elif la=='f':
                        y_true_file_f.append(na)
                        y_true_binary_f.append(y[ind])
                    elif la=='v':
                        y_true_file_v.append(na)
                        y_true_binary_v.append(y[ind])
                    elif la=='p':
                        y_true_file_p.append(na)
                        y_true_binary_p.append(y[ind])
                    elif la=='b':
                        y_true_file_b.append(na)
                        y_true_binary_b.append(y[ind])
                    elif la=='o':
                        y_true_file_o.append(na)
                        y_true_binary_o.append(y[ind])
                    result=[na,la,p_y_pred[ind]]
                    result_roll.append(result)
                    ind=ind+1
                
                
                pred_roll.append( pred )
                gt_roll.append( y )
    
    pred_roll = np.array( pred_roll )
    gt_roll = np.array( gt_roll )
    #write csv for EER computation
    csvfile=file('result.csv','wb')
    writer=csv.writer(csvfile)
    #writer.writerow(['fn','label','score'])
    writer.writerows(result_roll)
    csvfile.close()
    
    # calculate prec, recall, fvalue
    prec, recall, fvalue = prec_recall_fvalue( pred_roll, gt_roll, thres )
    # EER for each tag : [ 'c', 'm', 'f', 'v', 'p', 'b', 'o', 'S' ]
    EER_c=eer.compute_eer('result.csv', 'c', dict(zip(y_true_file_c, y_true_binary_c)))
    EER_m=eer.compute_eer('result.csv', 'm', dict(zip(y_true_file_m, y_true_binary_m)))
    EER_f=eer.compute_eer('result.csv', 'f', dict(zip(y_true_file_f, y_true_binary_f)))
    EER_v=eer.compute_eer('result.csv', 'v', dict(zip(y_true_file_v, y_true_binary_v)))
    EER_p=eer.compute_eer('result.csv', 'p', dict(zip(y_true_file_p, y_true_binary_p)))
    EER_b=eer.compute_eer('result.csv', 'b', dict(zip(y_true_file_b, y_true_binary_b)))
    EER_o=eer.compute_eer('result.csv', 'o', dict(zip(y_true_file_o, y_true_binary_o)))
    EER=(EER_c+EER_m+EER_v+EER_p+EER_f+EER_b+EER_o)/7.0
    print prec, recall, fvalue
    print EER_c,EER_m,EER_f,EER_v,EER_p,EER_b,EER_o
    print EER

if __name__ == '__main__':
    recognize()
