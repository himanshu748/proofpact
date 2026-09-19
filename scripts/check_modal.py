from backend.agents import ModalAgents
from backend.domain import create_project
public={'brief':'Build a small admin dashboard.','requirements':['Secure login','Analytics dashboard','CSV export','OTP verification'],'previous':{'price_minor':750000,'deadline':'2026-09-21'}}
a=ModalAgents()
for role,private in [('builder',{'private_limit_minor':650000,'opening_minor':800000,'deadline':'2026-09-21','notes':'Payments excluded.'}),('client',{'private_limit_minor':800000,'opening_minor':500000,'deadline':'2026-09-23','notes':'OTP is essential.'})]:
    offer=a.offer(role,public,private)
    print(role,offer.model_dump(mode='json'))
