from wxpy import *
import re
import time
import sys
import pymongo
import codecs
from wordcloud import WordCloud
import jieba
from collections import Counter


def initDataBase():
	#connect to the database
	conn = pymongo.MongoClient('127.0.0.1',27017)
	message_collections = conn.wxmessage.message
	
	return message_collections
	
def initOrderList():
	orderlist={}
	
	# robot order
	orderlist['ORDER_START_AI']  = "/start"
	orderlist['ORDER_STOP_AI']   = "/stop"
	orderlist['ORDER_END_AI']    = "/end"
	orderlist['ORDER_AUTO_RES']  = "autoresponse"

	# to finish later...
	orderlist['ORDER_ASK']       = "#ask#"
	orderlist['ORDER_ABORT']     = "abort"

	# generate word cloud
	orderlist['ORDER_WORD_CLOUD']= "/hot"
	
	return orderlist

'''
	from raw content find the withdraw msgid
	input : raw message
	output: msgid of the withdraw message
'''
def findMsgId(raw):
	pat = "<msgid>(.*)</msgid>"
	pat_group = "&lt;msgid&gt;(.*)&lt;/msgid"
	msgId = ""
	if re.search(pat,raw) ==None :
		msgId = re.search(pat_group,raw).group(1)
	else :
		msgId = re.search(pat,raw).group(1)
	return int(msgId)
	
	

class WeChatEx(object):

	def __init__(self):
	
		self.message_collections = initDataBase()
		self.orderlist = initOrderList()
		self.rob = Bot(cache_path = True)
		self.myself = self.rob.friends().search(self.rob.self.name)[0]
		
		ai_key = "5c7eacb58e4bf0937ab5e9624ce0f08f"
		self.AI = Tuling(api_key = ai_key)
		self.AI_TRIGGER = False
		self.AI_GROUP = []
		
		self.font = "msyh.ttc"
	
	def generate_wordcloud(self, target):
		stopwords = set([x.strip() for x in open("stopwords.txt",'r',encoding = 'utf-8').read().split('\n')])
		name = target
		result = self.message_collections.find({"$or":[{"receiver":name},{"sender":name}]}).sort([("time",-1)]).limit(200)
		content = (i['text'] for i in result)
		seg_list = (jieba.cut(temp) for temp in content)
		freq = Counter(word for item in seg_list for word in item if len(word) > 1 and word not in stopwords)
		wordcloud = WordCloud(font_path=self.font).generate_from_frequencies(freq)
		wordcloud.to_file("wordcloud.png")
		self.myself.send_image("wordcloud.png")
	
	
	def handleNOTEmessage(self,msg = None):
		text = msg.text
		WITHDRAW = "撤回了一条消息"
		if text.find( WITHDRAW ) > 0:
			msgid = findMsgId(msg.raw['Content'])
			for item in self.rob.messages :
				if item.id == msgid :
					if item.type == TEXT:
						if item.member:
							rec = item.member.name
						else :
							rec = item.receiver.name
						postmsg = item.sender.name+'->' + rec + '撤回了消息:' + item.text
						self.myself.send_msg(postmsg)
						break
					elif item.type == PICTURE:
						item.get_file("picture.jpg")
						if item.member:
							rec = item.member.name
						else :
							rec = "None"
						postmsg = item.sender.name + '->' + rec + '撤回了图片'
						self.myself.send_msg(postmsg)
						self.myself.send_image("picture.jpg")
						break
						 
	def handleTEXTmessage(self,msg = None):
		# start AI
		if msg.sender == self.myself:
			if msg.text == self.orderlist['ORDER_START_AI'] :
				self.AI_TRIGGER = True
				if msg.receiver not in self.AI_GROUP and msg.receiver != self.myself:
					self.AI_GROUP.append(msg.receiver)
					postmsg = '对'+msg.receiver.name+'开启了自动回复'
					self.myself.send_msg(postmsg)
					
			elif msg.text == self.orderlist['ORDER_STOP_AI'] :
				if msg.receiver in self.AI_GROUP :
					self.AI_GROUP.remove(msg.receiver)
					postmsg = '对'+msg.receiver.name+'关闭了自动回复'
					self.myself.send_msg(postmsg)
			elif msg.text == self.orderlist['ORDER_END_AI'] :
				self.AI_TRIGGER = False
				self.AI_GROUP.clear()
				postmsg = '停止了自动回复功能'
				self.myself.send_msg(postmsg)
		
		# AI start to reply aotumaticly
		if (msg.sender in self.AI_GROUP)  and self.AI_TRIGGER :
			time.sleep(1)
			# close AI temporary
			self.AI.do_reply(msg,True)
			hour = time.localtime(time.time()).tm_hour
			if 3 <= hour <= 5:
				msg.sender.send("为了你的身体安全，请不要修仙（微笑）")


		elif self.orderlist['ORDER_WORD_CLOUD'] == msg.text :
			if msg.sender == self.myself :
				target = msg.receiver
			else :
				target = msg.sender
			self.generate_wordcloud(target.name)

		else :
			insert_result = self.message_collections.insert_one({
			 "sender":msg.sender.name,
			 "receiver":msg.receiver.name,
			 "text":msg.text,
			 "time":time.time()})
			#print (msg.text)




wechatex = WeChatEx()

# 接收类型为文字，图片，通知
receive_type=[TEXT,NOTE,PICTURE]
# handle message here
@wechatex.rob.register(msg_types=receive_type,except_self=False)
def handle_messages(msg):
	# when someone withdraw a message
	if msg.type == NOTE :
		wechatex.handleNOTEmessage(msg)

	elif msg.type == TEXT:
		wechatex.handleTEXTmessage(msg)


embed()
