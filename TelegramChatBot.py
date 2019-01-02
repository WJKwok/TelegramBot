#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""
This Bot handles the return of QRCode-tagged reusable lunchboxes in conversation style.
"""

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler, CallbackQueryHandler)
import logging
import datetime
import gspread
from pyzbar.pyzbar import decode
from PIL import Image
from io import BytesIO
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)
memberSheet = client.open("Efpacked Box Tracking").get_worksheet(1)
stockSheet = client.open("Efpacked Box Tracking").sheet1

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

OPTION, REGISTER, SCANMORE, FEEDBACK, PAYNRIC, PAYBA, PAYPN = range(7)

#get next available row in sheets
def next_available_row(worksheet):
    str_list = filter(None, worksheet.col_values(1))
    return str(len(str_list)+1)

paymentDetail = "Payment Details"
checkPoint = "My Points"
returnBox = "Return a Box"
feedbackPM = "Feedback"
showMenu = "Menu"
bankTransfer = "Switch to Bank Transfer"
editBankTransfer = "Edit Bank Account"
usePayNow = "Switch to PayNow"
editPayNow = "Edit PayNow"
scanAnotherQR = "Return Another Box"

def start(bot, update):
    user = update.message.from_user
    try:
        cell = memberSheet.find('%s'%(user.id))
        keyboard = [[InlineKeyboardButton("Option 1", callback_data='1'),
                     InlineKeyboardButton("Option 2", callback_data='2')],
                    [InlineKeyboardButton("Option 3", callback_data='3')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Please choose:', reply_markup=reply_markup)
    except gspread.exceptions.CellNotFound:
        contact_keyboard = KeyboardButton(text="Send Mobile Number", request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
        update.message.reply_text(
            'Hello, %s! Uncle Lim here.\n\n'
            'Select \'Send mobile number\' so we can PayNow the deposit back to you.\n\n'
            'NOTE: If you do not have PayNow, you can opt for bank transfer later.'%(user.first_name),
            reply_markup=reply_markup)
    finally:
        return OPTION

def registerUserProcess(bot, update):
    contact = update.message.contact.phone_number
    userChat = update.message.from_user
    bot.send_chat_action(chat_id = userChat.id, action = ChatAction.TYPING)
    next_row = next_available_row(memberSheet)
    memberSheet.update_acell('A%s'%(next_row), '%s'%(contact))
    memberSheet.update_acell('B%s'%(next_row), '0')
    memberSheet.update_acell('C%s'%(next_row), '%s'%(userChat.id))
    memberSheet.update_acell('D%s'%(next_row), '%s'%(userChat.first_name))
    memberSheet.update_acell('F%s'%(next_row), 'PAYNOW')
    memberSheet.update_acell('G%s'%(next_row), '%s'%(contact))
    memberSheet.update_acell('H%s'%(next_row), '0')
    memberSheet.update_acell('J%s'%(next_row), '%s'%(userChat.username))
    custom_keyboard = [[returnBox],[checkPoint],[feedbackPM],[paymentDetail]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text("Yay, registered ✅\n"
                              "Ok, when you return box, Uncle will PayNow deposit to %s\n\n"
                              "Or you not as hip as Uncle, don't have PayNow? 😂\n\n"
                              "It's ok, even though troublesome, Uncle can bank transfer you. "
                              "Just select 'Payment Details' to edit 👌\n\n"%(contact),
                              reply_markup=reply_markup)
    return OPTION

def paymentMethod (bot, update):
    user = update.callback_query
    cell = memberSheet.find('%s'%(user.message.chat_id))
    rowNumber = cell.row
    userNo = memberSheet.acell('A%s'%(rowNumber)).value
    payMethod = memberSheet.acell('F%s'%(rowNumber)).value
    payDetail = memberSheet.acell('G%s'%(rowNumber)).value
    if payMethod == "PAYNOW":
        bot.answer_callback_query(user.id, text="hello bomalo!")
        bot.send_message(chat_id=user.message.chat_id, text="Selected option: {}".format(user.data))
        '''bot.edit_message_text(text="Selected option: {}".format(user.data),
                          chat_id=user.message.chat_id,
                          message_id=user.message.message_id)
        mobile_keyboard = [[editPayNow],[bankTransfer],[showMenu]]
        reply_markup = ReplyKeyboardMarkup(mobile_keyboard, one_time_keyboard=True)
        update.message.reply_text("Currently, Uncle will PayNow deposits to %s\n\n"
                              "You can edit payment details:\n"
                              "1) Edit PayNow\n"
                              "2) To receive deposit via bank transfer, select 'Switch to Bank Transfer'\n\n"%(payDetail),
                              reply_markup=reply_markup)'''
    elif payMethod == "BANK":
        bankAcc_keyboard = [[editBankTransfer],[usePayNow],[showMenu]]
        reply_markup = ReplyKeyboardMarkup(bankAcc_keyboard, one_time_keyboard=True)
        update.message.reply_text("Currently, Uncle will transfer deposits to %s\n\n"
                              "You can edit payment details:\n"
                              "1) Edit Bank Acc\n"
                              "2) To receive deposit via PayNow, select 'Switch to PayNow'\n\n"%(payDetail),
                              reply_markup=reply_markup)
    return REGISTER

def bankAcc(bot, update):
    update.message.reply_text(
            'Bank account to transfer to?\ne.g. POSB 123-45678-9\n\n'
            'NOTE: Send in ONE single message.\n\n'
            'To return to menu click: /start')
    return PAYBA

def payNowAcc(bot, update):
    update.message.reply_text(
            'Mobile or NRIC to PayNow to?\ne.g. 82345678\ne.g. S9123456Z\n\n'
            'NOTE: Send in ONE single message.\n\n'
            'To return to menu click: /start')
    return PAYPN

def receivedBA(bot, update):
    payDetails = update.message.text
    user = update.message.from_user
    cell = memberSheet.find('%s'%(user.id))
    rowNumber = cell.row
    memberSheet.update_acell('F%s'%(rowNumber), 'BANK')
    memberSheet.update_acell('G%s'%(rowNumber), '%s'%(payDetails))
    keyboard = [[returnBox],[checkPoint],[feedbackPM],[paymentDetail]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
            'Got it! Uncle will transfer deposits to %s'%(payDetails),
            reply_markup=reply_markup)
    return OPTION

def receivedMN(bot, update):
    payDetails = update.message.text
    user = update.message.from_user
    cell = memberSheet.find('%s'%(user.id))
    rowNumber = cell.row
    memberSheet.update_acell('F%s'%(rowNumber), 'PAYNOW')
    memberSheet.update_acell('G%s'%(rowNumber), '%s'%(payDetails))
    keyboard = [[returnBox],[checkPoint],[feedbackPM],[paymentDetail]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
            'Got it! From now, Uncle will PayNow deposits to %s'%(payDetails),
            reply_markup=reply_markup)
    return OPTION

def checkPoints(bot, update):
    user = update.message.from_user
    cell = memberSheet.find('%s'%(user.id))
    rowNumber = cell.row
    currentScore = int(memberSheet.acell('B%s'%(rowNumber)).value)
    keyboard = [[returnBox],[checkPoint],[feedbackPM],[paymentDetail]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
            "Your current score is %s\n"
            "So little! Uncle believe you can get more! 💪"%(currentScore),
            reply_markup=reply_markup)

    return OPTION

def scanQR(bot, update):
    user = update.message.from_user
    cell = memberSheet.find('%s'%(user.id))
    keyboard = [[returnBox],[checkPoint],[feedbackPM],[paymentDetail]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
        "Have a box for Uncle? Great!\n"
        "Snap and upload a photo of the QR Code to Uncle.\n\n"
        "Select the 📎 icon, snap a photo, send it over!",
        reply_markup=reply_markup)

    return OPTION

def scanQRProcess(bot, update):
    user = update.message.from_user
    bot.send_chat_action(chat_id = user.id, action = ChatAction.TYPING)
    keyboard = [[returnBox],[checkPoint],[feedbackPM],[paymentDetail]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    photo_file = update.message.photo[-1].get_file()
    with BytesIO() as f:
        photo_file.download(out=f)
        f.seek(0)
        barcode = decode(Image.open(f))
        try:
            data = barcode[0].data
            print(data)
            try:
                cell = stockSheet.find('%s'%(data))
                rowNumber = cell.row
                status = stockSheet.acell('B%s'%(rowNumber)).value
                print(status)
                if status == "Borrowed":
                    stockSheet.update_acell('F%s'%(rowNumber), '%s'%(datetime.datetime.now()))
                    count = int(stockSheet.acell('G%s'%(rowNumber)).value) + 1
                    stockSheet.update_acell('G%s'%(rowNumber), '%s'%(count))
                    returnNames = str(stockSheet.acell('H%s'%(rowNumber)).value) + ", %s"%(user.username)
                    stockSheet.update_acell('H%s'%(rowNumber), '%s'%(returnNames))
                    payCell = memberSheet.find('%s'%(user.id))
                    payRow = payCell.row
                    payDetail = memberSheet.acell('G%s'%(payRow)).value
                    boxCount = int(memberSheet.acell('H%s'%(payRow)).value) + 1
                    memberSheet.update_acell('H%s'%(payRow), '%s'%(boxCount))
                    boxIDs = str(memberSheet.acell('I%s'%(payRow)).value) + ", %s"%(data)
                    memberSheet.update_acell('I%s'%(payRow), '%s'%(boxIDs))
                    update.message.reply_text(
                        'Noted! Drop it off in a collection box by today!\n\n'
                        'At the end of the day when Uncle collect and verify your return, '
                        'Uncle will refund your $1.50 deposit to %s'%(payDetail),
                        reply_markup=reply_markup)
                elif status == "Event":
                    update.message.reply_text(
                        'Ooo... a Tedx event box. Please return it to a Tedx facilitator. \n\n'
                        'Thank you for making Tedx Pickering Street one container closer to being a zero-waste event 💪',
                        reply_markup=reply_markup)
                else:
                    update.message.reply_text(
                        'Don\'t bluff Uncle leh 😓\n'
                        'This box has been returned alr leh.',
                        reply_markup=reply_markup)
            except gspread.exceptions.CellNotFound:
                update.message.reply_text(
                    'Why you send random QR Code?\n'
                    'Uncle very busy, don\'t disturb leh 😠',
                    reply_markup=reply_markup)
        except IndexError:
            update.message.reply_text(
                'What you send Uncle?\n'
                'Uncle colour blind, can only read QR code 😒',
                reply_markup=reply_markup)

    return OPTION

def contactUs(bot, update):
    user = update.message.from_user
    cell = memberSheet.find('%s'%(user.id))
    update.message.reply_text(
            'Don\'t need to cry\n'
            'Come, tell Uncle what\'s wrong 😥\n\n'
            'NOTE: Send in ONE single message.\n\n'
            'To return to menu click: /start')
    return FEEDBACK

def messageSent(bot, update):
    feedback = update.message.text
    user = update.message.from_user
    cell = memberSheet.find('%s'%(user.id))
    rowNumber = cell.row
    memberSheet.update_acell('E%s'%(rowNumber), '1')
    keyboard = [[returnBox],[checkPoint],[feedbackPM],[paymentDetail]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
            'So you\'re telling Uncle:\n%s \n\n'
            'Let Uncle have a think on how to help, then reply you ASAP!'%(feedback),
            reply_markup=reply_markup)
    bot.send_message(chat_id=242432855, text='@%s: %s'%(user.username, feedback))

    return OPTION

def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Noo, Uncle will miss you 😭\n'
        'If you want to talk to Uncle again, click: /start',
        reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def refreshToken(bot, job):
    global scope, creds, client, memberSheet, stockSheet
    scope = ['https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    memberSheet = client.open("Efpacked Box Tracking").get_worksheet(1)
    stockSheet = client.open("Efpacked Box Tracking").sheet1
    bot.send_message(chat_id=242432855, text='Token Refreshed :)')

def main():
    # Where bot token should be.
    updater = Updater("XXXXXXXXXXXXX")
    job = updater.job_queue
    job.run_repeating(refreshToken, interval=3540, first=0)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            OPTION: [RegexHandler(paymentDetail, paymentMethod),
                     RegexHandler(checkPoint, checkPoints),
                     RegexHandler(returnBox, scanQR),
                     RegexHandler(feedbackPM, contactUs),
                     MessageHandler(Filters.photo, scanQRProcess),
                     MessageHandler(Filters.contact, registerUserProcess),
                     CallbackQueryHandler(paymentMethod, pattern="1")],

            SCANMORE: [RegexHandler(scanAnotherQR, scanQR),
                       RegexHandler(showMenu, start)],

            REGISTER: [RegexHandler(bankTransfer, bankAcc),
                       RegexHandler(editBankTransfer, bankAcc),
                       RegexHandler(usePayNow, payNowAcc),
                       RegexHandler(editPayNow, payNowAcc),
                       RegexHandler(showMenu, start)],

            FEEDBACK: [MessageHandler(Filters.text, messageSent)],

            PAYBA: [MessageHandler(Filters.text, receivedBA)],

            PAYPN: [MessageHandler(Filters.text, receivedMN)],
        },

        fallbacks=[CommandHandler('cancel', cancel),
                   CommandHandler('start', start)]

    )

    dp.add_handler(conv_handler)
    # log all errors
    dp.add_error_handler(error)
    # Start the Bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
