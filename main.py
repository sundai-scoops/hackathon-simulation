from lib import simulate_hackathon_turn, agents
import time


def main():
    turn = 1
    while True:
        print(f"Turn {turn}")
        simulate_hackathon_turn()
        print(agents)
        time.sleep(1)
        turn += 1


main()
