import argparse
import os
import platform
import shutil
import time
from pathlib import Path

import math
import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

import utils_1 as utils

#Robot embedded messages python bindings - Jetson needs setup
from rem import rem

#Serial communication
import serial

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import (
    check_img_size, non_max_suppression, apply_classifier, scale_coords,
    xyxy2xywh, plot_one_box, strip_optimizer, set_logging)
from utils.torch_utils import select_device, load_classifier, time_synchronized


def detect(save_img=False):
    out, source, weights, view_img, save_txt, imgsz, conn = \
        opt.output, opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size, opt.conn
    webcam = source.isnumeric() or source.startswith(('rtsp://', 'rtmp://', 'http://')) or source.endswith('.txt')

    # Initialize
    set_logging()
    device = select_device(opt.device)
    if os.path.exists(out):
        shutil.rmtree(out)  # delete output folder
    os.makedirs(out)  # make new output folder
    half = device.type != 'cpu'  # half precision only supported on CUDA
    
    #Parameter definition
    print(conn)    
    angle = 0
    rho = 0
    saw_ball = 0
    theta = 0
    theta_increment = 3*math.pi/4
    increment = math.pi/48


    if conn:
        serial_port_1 = serial.Serial(
        port="/dev/ttyACM0",
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        )
        # Wait a second to let the port initialize
        serial_port = utils.openContinuous(timeout=0.01)
        time.sleep(1)
    
    # Load model 
    model = attempt_load(weights, map_location=device)  # load FP32 model
    imgsz = check_img_size(imgsz, s=model.stride.max())  # check img_size
    if half:
        model.half()  # to FP16

    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model'])  # load weights
        modelc.to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = True
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz)
    else:
        save_img = True
        dataset = LoadImages(source, img_size=imgsz)

    # Get names and colors
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    # Run inference
    t0 = time.time()
    img = torch.zeros((1, 3, imgsz, imgsz), device=device)  # init img
    _ = model(img.half() if half else img) if device.type != 'cpu' else None  # run once
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        t1 = time_synchronized()
        pred = model(img, augment=opt.augment)[0]

        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)
        
        hasBall = 0
        
             
        
        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if webcam:  # batch_size >= 1
                p, s, im0 = path[i], '%g: ' % i, im0s[i].copy()
            else:
                p, s, im0 = path, '', im0s
            
            
            #Add deadzone to the image

            cv2.rectangle(im0, (round(im0.shape[1]*0.45),0), (round(im0.shape[1]*0.55),im0.shape[0]), (0,0,255) , thickness=3, lineType=cv2.LINE_AA)
            
            save_path = str(Path(out) / Path(p).name)
            txt_path = str(Path(out) / Path(p).stem) + ('_%g' % dataset.frame if dataset.mode == 'video' else '')
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh

                
            if det is not None and len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += '%g %ss, ' % (n, names[int(c)])  # add to string

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    
                    if save_txt:  # Write to file  
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh           
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * 5 + '\n') % (cls, *xywh))  # label format

                    
                    if save_img or view_img:  # Add bbox to image
                        label = '%s %.2f' % (names[int(cls)], conf)
                        plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=3)
                    
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                    #Get Object Coordinates
                    mid_x = xywh[0]
                    mid_y = xywh[1]
                    box_w = xywh[2]
                    box_h = xywh[3]
                    #print mid coordinates of the box
                    print('Mid coordinates of box,w, h: %.3f,%.3f,%.3f,%.3f' % (mid_x,mid_y, box_w, box_h))
                    
                    
                    
                    if (mid_x < 0.45):
                        #ROBOT TURN LEFT
                        angle = angle + increment #rad/s
                        print('LEFT %.4f', angle)
                        rho = 0
                        angularControl = 0 #angular velocity control
                        
                    elif (mid_x > 0.55): 
                        #ROBOT TURN RIGHT
                        angle = angle - increment #rad/s
                        print('RIGHT %.4f', angle)
                        rho = 0
                        angularControl = 0 #angular velocity control
                    
                    else: 
                        #DRIVE STRAIGHT TO THE BALL
                        angle = angle + 0 #rad/s
                        print('STRAIGHT %.4f', angle)
                        rho = rho + 0.1 #m/s
                        #if saw_ball:
                            #theta = theta #----> INSERT VALUE FOR THE ROBOT TO MOVE IN THE DIRECTION OF THE CAMERA
                        angularControl = 0 #angular velocity control
                        saw_ball = 1
            else:
                if not(hasBall):
                    angle = angle + increment #rad/s
                    print('NOBALL %.4f', angle)
                    rho = 0
                    angularControl = 0 #angular velocity control
                else: 
                    #STOP THE ROBOT
                    angle = angle + 0 #rad/s
                    rho = 0
                    angularControl = 0 #angular velocity control      
            
            if conn:
                #Constructing the packet
                cmd = rem.ffi.new("RobotCommand*")
                cmd.header = rem.lib.PACKET_TYPE_ROBOT_COMMAND
                cmd.id = 3

                #check value of angle
                
                if angle > math.pi*2:
                            angle = angle - math.pi*2

                if angle < -math.pi*2:
                            angle = angle + math.pi*2

                cmd.angle = angle
                #cmd.rho = rho
                #cmd.theta = theta
                #cmd. angularControl = angularControl

                packet = rem.ffi.new("RobotCommandPayload*")
                rem.lib.encodeRobotCommand(packet, cmd)

                #Sending the packet
                try:
                    serial_port.write(packet.payload)
                    print("         angle : %.4f" % cmd.angle);
                except KeyboardInterrupt:
                    print("Exiting Program")

                except Exception as exception_error:
                    print("Error occurred. Exiting Program")
                    print("Error: " + str(exception_error))

                
            # Print time (inference + NMS)
            print('%sDone. (%.3fs)' % (s, t2 - t1))

            # Stream results
            if view_img:
                cv2.imshow(p, im0)
                if cv2.waitKey(1) == ord('q'):  # q to quit
                    
                    cv2.destroyAllWindows()
                    raise StopIteration

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'images':
                    cv2.imwrite(save_path, im0)
                else:
                    if vid_path != save_path:  # new video
                        vid_path = save_path
                        if isinstance(vid_writer, cv2.VideoWriter):
                            vid_writer.release()  # release previous video writer

                        fourcc = 'mp4v'  # output video codec
                        fps = vid_cap.get(cv2.CAP_PROP_FPS)
                        w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
                    vid_writer.write(im0)

    if save_txt or save_img:
        print('Results saved to %s' % Path(out))
        if platform.system() == 'Darwin' and not opt.update:  # MacOS
            os.system('open ' + save_path)

    print('Done. (%.3fs)' % (time.time() - t0))
    
    serial_port.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='yolov5s.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='inference/images', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--output', type=str, default='inference/output', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.4, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.5, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--conn', type=bool, default=False)
    opt = parser.parse_args()
    print(opt)

    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt']:
                detect()
                strip_optimizer(opt.weights)
        else:
            detect()
