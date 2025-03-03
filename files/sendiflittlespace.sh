#!/bin/bash
#send mail via ssmtp to [mailbox] if space on [disk] is less, than [intnumber]%
#with mailbox [username] and [pass] (if needed) 
MAILBOX=
DISK=
FREE_SPACE=
THRESHHOLD=50
MAILBOX_USER=yagam0ver@yandex.ru  #$5
MAILBOX_PASS=kxdxqwlavhgfvlda     #$6
MAILBOX_PATTERN='^([a-zA-Z0-9_\-\.\+]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$'
DISK_PATTERN='^\/dev\/([a-zA-Z]{1}[-a-zA-Z0-9_\/]+)[^\/]$'

exec 1>/var/log/alertsmallspace.log

if [ -n "$1" ]
  then 
    if [[ "$1" =~ $MAILBOX_PATTERN ]] 
      then
        MAILBOX="$1"
      else
        echo "You need to define proper e-mail address"; exit 1
    fi
  else
    echo "You need to define e-mail address"; exit 1
fi

if [ -n "$2" ]
  then 
    if [[ "$2" =~ $DISK_PATTERN ]] 
      then
        DISK="$2"
        echo $DISK
      else
        echo "You need to define proper diskname"; exit 1
    fi
  else
    echo "You need to define diskname like /dev/sda1"; exit 1
fi

if [ -n "$3" ]
  then 
    if [[ "$3" =~ ^[0-9]{1,2}$ ]] 
      then
        THRESHHOLD="$3"
      else
        echo "Enter decimal integer for free space up to 99"; exit 1
    fi
  else
    THRESHHOLD="${3:-$THRESHHOLD}"
    echo "Free space is defined to 50%, or enter your value (int)% up to 99%, like 10"; exit 1
fi

if [ -n $(which ssmtp) ]  
  then 
    ssmtp_path=$(which ssmtp)
  else 
    echo "ssmtp seems not found"
fi

FREE_SPACE="$(df --output=pcent $DISK | tail -n 1)"
FREE_SPACE=$((100 - ${FREE_SPACE%\%}))

if [ $FREE_SPACE -lt $THRESHHOLD ]
  then 
    touch /var/log/alertsmallspace.log
    echo -e "Subject: very exquisite\n\nBackup script result is success\n" | \
             $ssmtp_path -v -au$MAILBOX_USER -ap$MAILBOX_PASS -f$MAILBOX_USER $MAILBOX
fi
