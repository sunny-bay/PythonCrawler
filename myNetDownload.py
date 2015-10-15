
#coding=utf8
import os
import shutil
import sys,time
import operator
import sgmllib
import threading
import urllib2
import cookielib

import re
import urlparse
import logging  
import Queue

#添加自定义打印，写文件，用打印级别控制

#############################################################################

def chooseDebuglevel(level):
    if level==0:
        return logging.CRITICAL#打印全关
    elif level == 1:
        return logging.ERROR
    elif level ==2:
        return logging.WARN
    elif level ==3:
        return logging.INFO
    elif level == 4:
        return logging.DEBUG
    elif level == 5:    
        return logging.NOTSET
    
debuglevel = chooseDebuglevel(4)

# 配置root日志信息
logging.basicConfig(level=debuglevel,
						format='[%(asctime)s][%(levelname)s][%(funcName)s] %(message)s',
	                    datefmt='%m-%d %H:%M',
	                    filename='debug.log',
	                    filemode='a')#这里的模式，因为使用了自定义的logger和root的logging
                        #若是模式都为w，则后面的打印logging会覆盖之前的logger

# 定义一个Handler打印INFO及以上级别的日志到sys.stderr
console = logging.StreamHandler()
console.setLevel(level=debuglevel)


# 设置日志打印格式
formatter =logging.Formatter("[%(levelname)s][%(funcName)s] %(message)s")
console.setFormatter(formatter)
# 将定义好的console日志handler添加到root logger
logging.getLogger('').addHandler(console)



#自定义一个logger
# create instance of logging
logger = logging.getLogger('mylogger')
logger.propagate = 0#消息不往上继续流
logger.setLevel(debuglevel)


# file handler
fh = logging.FileHandler('debug.log','w')
fh.setLevel(debuglevel)


# console handler
ch = logging.StreamHandler()
ch.setLevel(debuglevel)


# formatter
fmt = logging.Formatter("%(message)s")
fh.setFormatter(fmt)
ch.setFormatter(fmt)


# add formatter to handler
logger.addHandler(fh)
logger.addHandler(ch)

fh.flush()
fh.close()

#############################################################################





#Python的线程池实现

#替我们工作的线程池中的线程
class MyThread(threading.Thread):
    def __init__(self, workQueue, resultQueue,timeout=30, **kwargs):
        threading.Thread.__init__(self, kwargs=kwargs)
        #线程在结束前等待任务队列多长时间
        self.timeout = timeout
        self.setDaemon(True)#设置为守护线程
        self.workQueue = workQueue
        self.resultQueue = resultQueue
        self.start()
    def run(self):
        while True:
            try:
                #从工作队列中获取一个任务
                callable, args, kwargs = self.workQueue.get(timeout=self.timeout)
                #我们要执行的任务
                res = callable(args, kwargs)
                #把任务返回的结果放在结果队列中
                #self.resultQueue.put(res+" | "+self.getName()) 
                self.resultQueue.put(res)
            except Queue.Empty: #任务队列空的时候结束此线程
                break
            except:
                logging.debug( sys.exc_info())
                raise
class ThreadPool:
    def __init__( self, num_of_threads=20):
        self.workQueue = Queue.Queue()
        self.resultQueue = Queue.Queue()
        self.threads = []
        self.__createThreadPool( num_of_threads )
    
    def __createThreadPool( self, num_of_threads ):
        for i in range( num_of_threads ):
            thread = MyThread( self.workQueue, self.resultQueue )
            self.threads.append(thread)

    def wait_for_complete(self):
      #等待所有线程完成。
        while len(self.threads):
            thread = self.threads.pop()
            #等待线程结束
            if thread.isAlive():#判断线程是否还存活来决定是否调用join
                thread.join()
        logging.debug( "All jobs are are completed." ) 
    
    def add_job( self, callable, *args, **kwargs ):
       
        self.workQueue.put( (callable,args,kwargs) )
    def get_result(self, *args, **kwds):
        return self.resultQueue.get( *args, **kwds )#func的返回值

def printBegin():
    logger.debug( '*'*63 )
    logger.debug( 'Name:'+' '*18+'myDownLoad')
    logger.debug( 'Version:'+' '*15+'1.0')
    logger.debug( 'Author:'+' '*16+'zhaoshuang@ipanel.cn')
    logger.debug( 'Description:'+' ' * 11+'check and download the resource you want')
    logger.debug( '\n'+'*'*23+' Running begin '+'*'*25)
    logger.debug( 'INFO:\n Input the path and extendName what you will download, then will download all files to the dest Automatically!!!')
    logger.debug( 'Example:\nDownLoad Source Path:E:\dirtest,DownLoad Dest Path E:\savePath\n')

#打开页面，新建线程下载，发现文件就新建一个线程下载，发现新链接就新建线程加载，
#即是，加载一个线程，解析一个线程，下载文件一个线程


#建立10个线程的线程池
myThreadPool = ThreadPool(10)
#分别建立list保存即将下载的文件链接和新的web链接
myDownLoadFiles = []
myNewWebLink=[]
urlPathList = []


class DownloadFile():
    def __init__(self,inputPath,savePath,extendName):
        self.inputPath =inputPath
        self.fileDict={}
        self.savePath=savePath
        self.extendName =extendName
    
    def networkDownLoad(self,orginUrl):
        #根据输入的url,下载url中指定的所有文件
        #print '\ndownLoad.....'
         
        myThreadPool.add_job(downLoadWeb ,orginUrl)
 
        #此时看有多少文件list和页面list
        myThreadPool.wait_for_complete()


class MyRegMatch(object):
    def getAtag(self,string):
        a=r'<\s*a\s+href\s*=\s*\".*?\".*?>'
        result=self.match(a,string)
        return result
    def openHref(self,string):
        aTagData = self.getAtag(string)
        for Atag in aTagData:
            a=r'<\s*a\s+href\s*=\s*\"(.*?)\".*?>'
            result=re.search(a,Atag)
            href =  result.group(1)
            fullPath =getFullPath(href)
            if href.endswith('.bmp') or href.endswith('.jpg') or href.endswith('.gif') :
                myThreadPool.add_job( downLoadFile ,href )#有的A链接里有图片
            elif fullPath != []:
                myThreadPool.add_job( downLoadWeb ,fullPath )
    def getImg(self,string):
        img = r'<\s*img\s+src\s*=\s*\".*?\".*?>'
        result = self.match(img,string)
        return result
    def getBgImg(self,string):
        bgImg = r'background\s*:\s*url\s*\(.*?\)'
        result = self.match(bgImg,string)
        return result
    def openImg(self,string):
        imgTagData = self.getImg(string)
        for imgTag in imgTagData:
            img = r'<\s*img\s+src\s*=\s*\"(.*?)\".*?>'
            result = re.search(img,imgTag)
            if result:
                src = result.group(1)
                fullPath =getFullPath(src)
                if fullPath != []:
                    myThreadPool.add_job( downLoadFile,fullPath)
    def openBgImg(self,string):
        bgImgData = self.getBgImg(string)
        for bgImg in bgImgData:
            img = r'background\s*:\s*url\s*\(\"?(.*?)\"?\)'
            result = re.search(img,bgImg)
            if result:
                url = result.group(1)
                if getFullPath(url) != []:
                    myThreadPool.add_job( downLoadFile,url)


    def parseData(self,data):
        self.openHref(data)#打开link
        self.openImg(data)#下载web中的img标签
        self.openBgImg(data)#下载background:url(xxxx.jpg)这种形式的
    
    def match(self,pattern,string):
        a=re.compile(pattern)
        result=re.findall(a,string)
        return result


def getFullPath(url):
    
    if url.startswith("http") or url.startswith("https"):
        return url #规范的url
    if url =="#":
        return []
    if url.startswith("javascript:"):
        return []
    else:
        #‘需要拼接URL’
        logging.debug( "current url: %s ,need be patched!!!!\n"%url)
        newUrl = urljoin(urlPathList[0],url)
        return newUrl


def urljoin(base,url):
    join = urlparse.urljoin(base,url)
    
    url = urlparse.urlparse(join)
    path = os.path.normpath(url.path)
    path = path.replace('\\','/')
    return urlparse.urlunparse((url.scheme,url.netloc,path,url.query,url.fragment,''))

def downLoadWeb(*args, **kwargs):
    #print "downLoadFile args:"+str(args)
    try:
        url= args[0][0]
        #获取link的路径，方便后面拼接
        pos = url.rfind("/")#逆序位置
        filePathEx = url[:pos+1]
        urlPathList.append(filePathEx)
        if webHasDownload(url):
            logging.debug( url+ "  has already download!!!")
            return 
        myDownLoadFiles.append(url)
        logging.debug( "downloading Web: '%s'......\n"%url)
        logging.debug( "current thread: %s\n"%threading.current_thread())
        opener = MyOpener()
        myOpener =opener.getOpener()
        response = myOpener.open(url)
        pageData = response.read()
        #print pageData
        response.close()
        myThreadPool.add_job( parseWebData ,pageData )#下载完成后直接新建线程解析
        
    except urllib2.URLError as e:
        if hasattr(e, 'code'):
            logging.debug( 'Network Error HttpCode:%d ,url:%s'%(e.code,url))
            return    
    except:
        logging.debug(  sys.exc_info())


#实现方式一：使用python的parser模块解析(MyParser)
#实现方式二：使用python的正则自定义匹配(MyRegMatch)

def parseWebData(*args, **kwargs):
    logging.debug( 'parseWebData comming!!\n')
    logging.debug( "current thread: %s\n"%threading.current_thread())
    try:
        pageData= args[0][0]
       #方式一：
        myParser = MyParser()
        myParser.feed(pageData)
        #方式二：
        #myreg  = MyRegMatch()
        #myreg.parseData(pageData)
    except:
        logging.debug(  sys.exc_info())
    
    #return 'succeed'
def downLoadFile(*args, **kwargs):
    url= args[0][0]
    if fileHasDownload(url):
        logging.debug( url+ "  has already download!!!")
        return 
    myNewWebLink.append(url)
    logging.debug ("downLoadFile '%s' begin......\n"%url)
    logging.debug ( "current thread: %s\n"%threading.current_thread())
    
    try:
        opener = MyOpener()
        myOpener =opener.getOpener()
        response = myOpener.open(url)
    
        pageData = response.read()
        response.close()
        savePath="E:\\networkSave"#先把保存路径写死
        filePath = url.split('/')[-1]
        finalPath = savePath+"/"+filePath
        #print finalPath
        #dirPath = finalPath.s可以优化，通过url传入的新建目录
        if not os.path.isdir(savePath):
            os.makedirs(savePath)
        fileObj = file(finalPath,"wb")
        fileObj.write(pageData)  
        fileObj.close()
        logging.debug( "downLoadFile '%s' End......\n"%url)
    except urllib2.URLError as e:
        if hasattr(e, 'code'):
            logging.debug( 'Network Error HttpCode:%d ,url:%s'%(e.code,url))
            return 
    except:
         logging.debug(  sys.exc_info())
    
    #return 'succeed'
    
def webHasDownload(url): 
    '''判断是否已经抓取过这个页面'''
    return (True if url in myNewWebLink else False)

def fileHasDownload(url): 
    '''判断是否已经抓取过这个页面'''
    return (True if url in myNewWebLink else False)

    
class MyParser(sgmllib.SGMLParser):
    def start_a(self,attrs):
        hrefValue =[v for k, v in attrs if k=='href']
        for href in hrefValue:
            fullPath =getFullPath(href)
            if href.endswith('.bmp') or href.endswith('.jpg') or href.endswith('.gif') :
                
                myThreadPool.add_job( downLoadFile ,href )
                #myDownLoadFiles.append(href)
            else:
                myThreadPool.add_job( downLoadWeb ,fullPath )
                #myNewWebLink.append(href)
    def start_img(self,attrs):
        srcValue = [v for k, v in attrs if k=='src']
        for href in srcValue:
            fullPath =getFullPath(href)
            if href.endswith('.bmp') or href.endswith('.jpg') or href.endswith('.png')or href.endswith('.gif') :
                myThreadPool.add_job( downLoadFile ,href )
                #myDownLoadFiles.append(href)
            else:
                myThreadPool.add_job( downLoadWeb ,fullPath )
                #myNewWebLink.append(href)
        
              
            
class MyOpener():
	def __init__(self,username=''):
		self.httpHandler = urllib2.HTTPHandler(debuglevel=0)
		self.cookieJar=cookielib.LWPCookieJar(username)
		self.opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookieJar),self.httpHandler)
		urllib2.install_opener(self.opener)
	def getOpener(self):
		return self.opener
	def getCookieJar(self):
		return self.cookieJar
if __name__=="__main__":
    
    printBegin()
    
    Path="http://192.168.21.70/crawlTest/downloadTest.html"
    Path ="http://blog.163.com/photo.html"
    savePath='E:\savePath'
    extendName=['.mk']
    myDownLoad = DownloadFile(Path,savePath,extendName)
    myDownLoad.networkDownLoad(Path)
    