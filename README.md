POS PROJECT

This is a POS project that has 9 entitiess:
user
category
customer
payment
product
receipt
sale_item
sale
supplier 


Relationship between entities

product	 and   supplier	 have  Many to many	 because   "One supplier can supply many different products
                                           Many suppliers can supply the same product but different brands"
                                           
product	 and  category	 have   One to one	 because      A product can only be classified in a single category but a category can have many products.

product	and   sale	   have     one to many	 because       One sale can have one or more products

customer and	 user	     have   One to many	    because   One user can interact with many customers

customer	and payment	  have   One to many	 because     One customer can make many payments

sale_item	and payment	have   One to one	    because      One item is paid for only once

payment  and	receipt  have  	 One to one	 because          One payment has one receipt

sale	 and   sale_item	 have  One to many	 because        One sale contains one or more sale_items
