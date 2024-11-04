## Motivation

One difficulty I found in analyzing freight data is the ability to see what general lanes you run the most of. It is easy to make a pivot table in Excel on Origin -> Destination and count the number of times you ran that lane, but that doesnt capture the lanes that are *basically* the same. That is to say, lanes that are so similar they could be considered the same lane, but differ in location names.

Take for example, Los Angeles to Dallas. Your pivot table might have Los Angeles to Dallas sitting at 30 times a month for an average payout of $3500, but what you'd be missing is the Irvine to Mesquite lane that you ran 15 times at an average of $3800, or the Anaheim to Irving lane you ran 10 times at $3300. Overall, those are all the same lane and you are paying more on some loads than you should be.

Now you might be an expert in California to Texas freight and you might have the industry knowledge that those 3 lanes are all basically the same, which is great, but can you say the same for every lane that you run in a given month? For my branch of the company that includes ~ 7000 loads a month, ~3000 of which are on basic dry vans. With numbers like these, it's important to be able to algorithmically determine your most ran lanes, without resorting to simple pivot tables.

"But what about DAT markets" I hear some of you asking. Don't get me wrong, DAT markets are a useful tool, but they fall short when trying to find lanes that are similar to each other. A single change in zipcode can wind you up in a completely different DAT market, my method does not have this shortcoming.

![image](https://github.com/user-attachments/assets/c85fe113-e0dd-4cb5-a4f2-1b314b2e59b9)

The above image is the result of plotting every load in a single month, filtered down to dry van loads only. Some lanes can be seen easily, but their direction can't be determined from this visualization alone.

## The Process

Figuring out how to find similar lanes in a way that is time efficient took me a while. Like most of my problems I tried to find the simplified form of the problem. Essentially, what we are doing is comparing the similarity of two lines. Finding a similarity metric was the difficult part. Eventually I stumbled across "Flow Distance" from Tao and Thill (2016) which was used to find similar paths that citizens in Beijeng took from home to work, in order to make an efficient public transit system. One change I made from the paper was replacing their use of Euclidean distance with Haversine distance, which takes into account the curvature of the Earth. I also tweaked the Flow Distance formula, as they had it tuned to detect much smaller changes in lat / long, useful in Intra-city travel, whereas our purposes are in Intra-national travel.

Now that we have a metric, we can start our algorithm. As this is a problem that we do not already know the answer to, I needed an unsupervised learning algorithm. I tried a bunch of different clustering algorithms, but the one that gave the best results in the long run was OPTICS clustering, supplying our custom flow distance metric as the metric.

![image](https://github.com/user-attachments/assets/62657f5e-14b5-4024-b8a8-745c35774b1a)

The lanes that are colored the same are all of the lanes we have determined to be similar by clustering. Let's get rid of the non clustered lanes real quick.

![image](https://github.com/user-attachments/assets/b3321860-bf19-4bea-a908-9970e5a8055c)

Much better. This program also exports a few csv files which clarify some additional information about the clusters such as average rate per mile to the truck and from the customer. With this data you can use your market rate tool of choice to determine if you are over or under paying on your lanes. If you're over paying you know you have room to come down and save some money. If you are under paying you know some lanes that can be targeted more aggresively from your customers.

![image](https://github.com/user-attachments/assets/34eb6378-f236-4f65-9bf7-57e9fb1b46e9)


