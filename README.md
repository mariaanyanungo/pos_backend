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

ENTITY	    ENTITY	    RELATIONSHIP    	EXPLANATION

product	    supplier	  Many to many	    "One supplier can supply many different products
                                           Many suppliers can supply the same product but different brands"
                                           
product	   category	    One to one	       A product can only be classified in a single category but a category can have many products.

product	   sale	        one to many	       One sale can have one or more products

customer	 user	        One to many	       One user can interact with many customers

customer	 payment	     One to many	      One customer can make many payments

sale_item	 payment	   One to one	          One item is paid for only once

payment  	receipt    	 One to one	           One payment has one receipt

sale	    sale_item	   One to many	         One sale contains one or more sale_items
