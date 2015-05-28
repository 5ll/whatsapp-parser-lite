# -*- coding: utf-8 -*-
import datelib
import re
import operator

class ChatFeatures():

    def __init__(self):
        self.root_response_time    = []
        self.contact_response_time = []
        self.root_burst            = []
        self.contact_burst         = []
        self.initiations           = {}
        self.weekday               = {}
        self.shifts                = {}
        self.patterns              = {}
        self.proportions           = {}
        self.most_used_words       = {}

    def compute_response_time_and_burst(self, list_of_messages, root_name, senders, initiation_thrs=(60*60*8), burst_thrs=3):
        # perform the operations that are dependant on multiple messages
        # (response time, bursts)
        self.initiations = {}
        for s in senders:
            self.initiations[s] = 0
        t0 = list_of_messages[0].datetime_obj
        burst_count = 1
        for index, message in enumerate(list_of_messages):
            if index == 0:
                continue
            t1 = message.datetime_obj
            dt = t1 - t0

            # is sender the same as the last message?
            if message.sender != list_of_messages[index-1].sender:
                # sender changed, store the burst count and reset
                # print "sender changed: %s" % ( message.sender )
                if (dt.seconds > initiation_thrs):
                    self.initiations[message.sender] += 1
                #print("response time: %d\n" %(dt.seconds) )
                # is sender the root?
                if message.sender == root_name:
                    # store the burst count for the last sender, which is the
                    # opposite of current
                    if burst_count > burst_thrs:
                        self.contact_burst.append(burst_count)
                    self.root_response_time.append(dt.seconds)
                # is sender the contact?
                else:
                    # store the burst count for the last sender, which is the
                    # opposite of current
                    if burst_count > burst_thrs:
                        self.root_burst.append(burst_count)
                    self.contact_response_time.append(dt.seconds)
                
                # End of the first burst, restart the counter
                burst_count = 1

            else:
                # accumulate the number of messages sent in a row
                burst_count += 1
                # if burst_count >= 3:
                #     print"bursting: %d %s\n" % (burst_count, message.sender)
            t0 = t1

    def compute_messages_per_weekday(self, list_of_messages):
        self.weekday = {}
        for msg in list_of_messages:
            weekday = datelib.date_to_weekday(msg.date)
            if weekday not in self.weekday:
                self.weekday[weekday] = 1
            else:
                self.weekday[weekday] += 1
        return self.weekday

    def compute_messages_per_shift(self, list_of_messages):
        self.shifts = {
            "latenight": 0,
            "morning": 0,
            "afternoon": 0,
            "evening": 0
        }
        for msg in list_of_messages:
            hour = int(msg.time.split(":")[0])
            if hour >= 0 and hour <= 6:
                self.shifts["latenight"] += 1

            elif hour > 6 and hour <= 11:
                self.shifts["morning"] += 1

            elif hour > 11 and hour <= 17:
                self.shifts["afternoon"] += 1

            elif hour > 17 and hour <= 23:
                self.shifts["evening"] += 1
        return self.shifts

    def compute_messages_pattern(self, list_of_messages, senders, pattern_list):
        self.patterns = {}
        regexes = {}
        for pattern in pattern_list:
            self.patterns[pattern] = {}
            for sender in senders:
                self.patterns[pattern][sender] = 0
            # re=regular expression, .I = ignore case, .compile = convert to object
            regexes[pattern] = re.compile(re.escape(pattern), re.I)
        for msg in list_of_messages:
            for pattern in pattern_list:
                search_result = regexes[pattern].findall(msg.content)
                length = len(search_result)
                if length > 0:
                    if pattern not in self.patterns:
                        self.patterns[pattern][msg.sender] = length
                        print "This should never happen"
                    else:
                        self.patterns[pattern][msg.sender] += length
        return self.patterns

    def compute_message_proportions(self, list_of_messages, senders):
        total = 0
        self.proportions = {}
        for i in ["messages", "words", "chars", "qmarks", "exclams", "media"]:
            self.proportions[i] = {}
            for s in senders:
                self.proportions[i][s] = 0
        for msg in list_of_messages:
            self.proportions["messages"][msg.sender] += 1
            self.proportions["words"][msg.sender]    += len(msg.content.split(" "))
            self.proportions["chars"][msg.sender]    += len(msg.content)
            self.proportions["qmarks"][msg.sender]   += msg.content.count('?')
            self.proportions["exclams"][msg.sender]  += msg.content.count('!')
            self.proportions["media"][msg.sender] += (
                msg.content.count('<media omitted>') +
                msg.content.count('<image omitted>') +
                msg.content.count('<image omitted>') +
                msg.content.count('<audio omitted>') +
                msg.content.count('<‎immagine omessa>') +
                msg.content.count('<video omesso>') +
                msg.content.count('<‎vCROOTd omessa>') +
                msg.content.count('Photo Message') +
                msg.content.count('Video Message') +
                msg.content.count('Sticker')
            )
            total += 1
        self.proportions["total_messages"] = 0
        self.proportions["total_words"]    = 0
        self.proportions["total_chars"]    = 0
        self.proportions["total_qmarks"]   = 0
        self.proportions["total_exclams"]  = 0
        self.proportions["total_media"]    = 0

        self.proportions["avg_words"] = {}

        for s in senders:
            self.proportions["total_messages"] += self.proportions["messages"][s]
            self.proportions["total_words"] += self.proportions["words"][s]
            self.proportions["total_chars"] += self.proportions["chars"][s]
            self.proportions["total_qmarks"] += self.proportions["qmarks"][s]
            self.proportions["total_exclams"] += self.proportions["exclams"][s]
            self.proportions["total_media"] += self.proportions["media"][s]
            self.proportions["avg_words"][s] = self.proportions["words"][s] / self.proportions["messages"][s]

        return self.proportions

    def compute_most_used_words(self, list_of_messages, top=10, threshold=3):
        words_counter = {}
        self.most_used_words = {}
        for msg in list_of_messages:
            words = msg.content.split(" ")
            for w in words:
                if len(w) > threshold:
                    w = w.decode("utf8")
                    w = w.replace("\r", "")
                    w = w.lower()
                    if w not in words_counter:
                        words_counter[w] = 1
                    else:
                        words_counter[w] += 1
        sorted_words = sorted(words_counter.iteritems(), key=operator.itemgetter(1), reverse=True)
        self.most_used_words = sorted_words[:top]
        return self.most_used_words

    def compute_avg_root_response_time(self):
        if (len(self.root_response_time) != 0):
            return sum(self.root_response_time)/len(self.root_response_time)
        return 0

    def compute_avg_contact_response_time(self):
        if (len(self.contact_response_time) != 0):
            return sum(self.contact_response_time)/len(self.contact_response_time)
        return 0

    def compute_nbr_root_burst(self):
        return len(self.root_burst)
    
    def compute_nbr_contact_burst(self):
        return len(self.contact_burst)

    def compute_avg_root_burst(self):
        if (len(self.root_burst) != 0):
            return sum(self.root_burst)/len(self.root_burst)
        return 0

    def compute_avg_contact_burst(self):
        if (len(self.contact_burst) != 0):
            return sum(self.contact_burst)/len(self.contact_burst)
        return 0

    def compute_root_initation_ratio(self, root, contact):
        if (self.initiations[contact] != 0):
            return self.initiations[root] / self.initiations[contact]
        return 0