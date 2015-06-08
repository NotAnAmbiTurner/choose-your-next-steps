#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
import cgi
import urllib
import jinja2

from google.appengine.api import users
from google.appengine.ext import ndb

PARENT_ROOT = 'parent_root'

lessons_list = [# list of all chapters and all lessons, used to build validation lists
    ["0",["Welcome to the Nanodegree Program","The Basics of the Web and HTML","Stage 0: Getting Started with HTML","How Learning to Code Works"]],
    ["1",["Stage 1 Intro: Make Your Web Page","1.1","1.2","1.3"]],
    ["2",["Stage 2 Intro: Automate Your Page","2.1","2.2","2.3","2.4","2.5","2.6","2.7"]],
    ["3",["Stage 3 Intro: Program with Objects","3.1","3.2","3.3a","3.3b","3.3c","3.4a","3.4b"]],
    ["4",["Stage 4 Intro: Allow Comments", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8"]],
    ["5",["5.1","5.2","5.3", "5.4", "5.5", "5.6"]],
]
    
errors = {}
errors['title'] = 'There must be an updated title in the <b>title</b> area, and it cannot be empty.'
errors['content'] = 'There must be updated content in the <b>content</b> area, and it cannot be empty.'
errors['lesson'] = 'You must enter a <b>new</b> lesson, and you cannot select a chapter'
errors['add_new'] = 'There must be content in <b>both</b> the title and content areas, and you must choose a valid lesson (<b>not</b> a chapter name).'
errors[None] = " "
    
lessons_reverse_dictionary = {} # list used to derive chapter from dict[lesson]
lessons_validate_list = [] # list of all the lessons, used to validate input later
for x in lessons_list:
    for y in x[1]:
        lessons_validate_list.append(y) # output [all lesssons]
        lessons_reverse_dictionary[y] = x[0] # output {lesson: unit}

template_dir = 'templates' # directory for templates
jinja2_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                autoescape = True) #load jinja2 environment. I'm not sure how this actually works tbh

class NodeClass(ndb.Model):
    """Main model for representing notes heading (aka title), content, associated unit (aka chapter) number, and associated lesson (eg. lesson 4.1)"""
    title = ndb.StringProperty(indexed=False)
    content = ndb.StringProperty(indexed=False)
    unit = ndb.StringProperty(indexed=False)
    lesson = ndb.StringProperty(indexed=False)
    
class Handler(webapp2.RequestHandler):
    """creates new master class for handling requests using jinja2"""
    
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, template, **params):
        t = jinja2_env.get_template(template)
        return t.render(params)
        
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainHandler(Handler):
    '''loader for the main_content.html page'''

    def post(self):
        
        nodes = NodeClass.query(ancestor=ndb.Key("Node", PARENT_ROOT or '*notitle*')) # gets all database entries
        
        self.response.write( # writes out that the delete function is currently offline
        '''delete currently disabled, but here is the code:
        
        if self.request.get('database_delete'):
            for x in nodes:
                self.response.write("entry <b>" + str(x.title) + "</b> deleted<br>") # writes to page that each entry is deleted
                x.key.delete() # deletes all entries
            self.response.write("**** entire database deleted ****") # writes that all entries were deleted'''.replace('\n','<br>'))
            
        self.get()
    
    def get(self):
        nodes = NodeClass.query(ancestor=ndb.Key("Node", PARENT_ROOT or '*notitle*')) # gets (I thought it was a list, but apparently it's a Query object) of all nodes with parent PARENT_ROOT (the only parent I use, unlike in the guestbook app where multiple guestbooks would have separate parents)
        
        toc_nodes_list = self.generate_toc_nodes_list(nodes) # generate a dict for use by the jinja2 template in building a TOC
        
        self.render("main_content.html", content=nodes, lessons_list=lessons_list, toc_nodes_list=toc_nodes_list) # render the main page jinja2 template
        
    def generate_toc_nodes_list(self, nodes):
        """returns a dict of nodes(NodeClass) with lesson title as the key, suitable for use in building the toc by main_content.html of format dictionary[lesson_name]:[list of NodeClass objects from lesson_name]"""
        
        return_dict_lessons = {} # create blank dict to return
        
        for x in nodes: # loop through all nodes (items of class NodeClass)
            if not x.lesson in return_dict_lessons.keys(): # if the lesson is not a key
                return_dict_lessons[x.lesson] = [x] # create a dictionary entry with the lesson as the key, and the node (incl. lesson, unit, title, content) as the first item in a list
            else: # if a dictionary entry already exists for that lesson
                return_dict_lessons[x.lesson].append(x) # add the node to the list
        
        return return_dict_lessons # return data in format dictionary[lesson_name]:[list of NodeClass objects from lesson_name, NodeClass object 2, NodeClass object 3, ...]
        
class AddNew(MainHandler):
    '''subclass of the loader for the AddNew (add_new.html) page'''
    
    def get(self, error=None):
        from_toc = self.request.get('q') # get value of lesson, if redirected from TOC (used by jinja2 template to auto-select correct lesson when linked from main page click to add" link)
        
        self.render("add_new.html", error = errors[error], lessons_list=lessons_list, from_toc=from_toc) # render page, pass in args for jinja2 template
    
    def post(self):
        
        if self.request.get("return_without_changes"): # if post asks to return to main page without changes
            self.redirect("/") # return to main page without changes
        else:    
            new_lesson = self.request.get('select_lesson') # get the lesson selected
            if new_lesson in lessons_validate_list: # if the selected lesson is a valid lesson
                node = NodeClass(parent=ndb.Key("Node", PARENT_ROOT or '*notitle*'), title=self.request.get('title'), content=self.request.get('content'),lesson=new_lesson, unit=lessons_reverse_dictionary[new_lesson]) # create new node class to pass in to validation functian
            else: # if not a valid lesson
                node = NodeClass(parent=ndb.Key("Node", PARENT_ROOT or '*notitle*'), title=self.request.get('title'), content=self.request.get('content'),lesson=new_lesson, unit='') #  create a new node class with a unit that will not pass validation, but also won't cause an error when lessons_reverse_dictionary[new_lesson] is found to not exist
            
            self.validate_post_and_redirect_new(node) # pass node to validation function
    
    def validate_post_and_redirect_new(self, node):
        '''validates the input of the page's content, and redirects as appropriate - if content is accepted, redirects to the main page or to the same page. If content is rejected, stays on the same page to allow entering of content that complies with validation requirements'''
        
        if node.title != "" and node.content != "" and (node.lesson in lessons_validate_list): # validates input
            node.put() # stores node
            self.redirect_url() # redirects to URL
        else:
            self.get(error='add_new') # writes error, and re-loads page BUT DELETES CONTENT
            
    def redirect_url(self):
        '''checks to see which URL to be redirected to (based on user input), and redirects'''
        
        if self.request.get('stay'):
            self.get()
        else:
            self.redirect('/')
            
    def node_from_urlsafe_key_in_url(self):
        '''output the NodeClass object, input: related URLsafe key'''
        key_string = self.request.get('node')
        key = ndb.Key(urlsafe=key_string)
        node = key.get()
        return node

        
class EditHandler(AddNew):
    def get(self, error=None):
        node = super(EditHandler, self).node_from_urlsafe_key_in_url() # gets the node related to the URLsafe key in the redirect URL
        self.render("change_page.html", error = errors[error], node=node, lessons_list=lessons_list) # renders the page with the content from the node (passes in the node, the template uses the node's parameters to render the page)
        
    def post(self):
        node = super(EditHandler, self).node_from_urlsafe_key_in_url() # gets the node related to the URLsafe key in the redirect URL
        
        if self.request.get("return_without_changes"): # returns to main page
            self.redirect("/")
        
        if self.request.get("title_change"): # changes title
            new_title = self.request.get('title')
            if new_title and new_title != node.title: # only if the title was changed, and is not empty
                node.title = new_title
                node.put()
                super(EditHandler, self).redirect_url()
            else:
                self.get(error='title')
        
        if self.request.get("content_change"): # changes title
            new_content = self.request.get('content')
            if new_content and new_content != node.content: # only if the content was changed, and is not empty
                node.content = new_content
                node.put()
                super(EditHandler, self).redirect_url()
            else:
                self.get(error = "content")
                
        if self.request.get("lesson_change"): # changes title
            new_lesson = self.request.get('select_lesson')
            if new_lesson != node.lesson and (new_lesson in lessons_validate_list): # only if the lesson was changed, and is a valid lesson
                node.lesson = new_lesson
                node.unit = lessons_reverse_dictionary[new_lesson]
                node.put()
                super(EditHandler, self).redirect_url()
            else:
                self.get(error='lesson')

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/edit', EditHandler),
    ('/new', AddNew),
], debug=True)

