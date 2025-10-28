(define (domain virtualhome)
  (:requirements :strips :typing)

  (:types
    objectt - object
    agent - object
    room - object

    sittable-objectt - objectt  ;; an object the agent can sit on
    switchable-objectt - objectt  ;; an object the agent can switch on/off
    grabbable-objectt - objectt  ;; an object the agent can grab (hold)

    static-objectt - objectt  ;; an object that does not move (e.g., furniture, appliances, containers)
    surface-objectt - static-objectt  ;; a static object that has a surface the agent can put things on
    container-objectt - static-objectt  ;; a static object that can contain other objects (e.g., fridge, drawer)

  )

  (:predicates
    ;; --- Agent state ---
    (at ?agent - agent ?loc - room)
    (sitting ?agent - agent)
    (standing ?agent - agent)
    (holding ?agent - agent ?obj - grabbable-objectt)
    (close ?agent - agent ?obj - objectt)
    (has-free-hand ?agent - agent)
    (ready-to-move-to-next-obj ?agent - agent)
    (not-ready-to-move-to-next-obj ?agent - agent)

    ;; --- Object states ---
    (on ?appl - switchable-objectt)
    (off ?appl - switchable-objectt)
    (is-open ?cont - container-objectt)
    (is-closed ?cont - container-objectt)

    ;; --- Reachability types ---
    (always-reachable ?obj - static-objectt)
    (reachable-on-surface ?obj - objectt ?surf - surface-objectt)  ;; obj is reachable when placed on surface surf
    (reachable-inside-room ?obj - objectt ?loc - room)  ;; obj is reachable when placed inside room loc
    ;; there is no need for reachable-inside-container since it is being handled by is-open predicate

    ;; --- Spatial relations ---
    (in-room ?obj - objectt ?room - room)
    (in-container ?obj - objectt ?cont - container-objectt)
    (on-surface ?obj - objectt ?surf - surface-objectt)
    (close-objects ?obj1 - objectt ?obj2 - objectt)

  )

  ;; ---------------------------------------------------------------------------
  ;; MOVEMENT ACTIONS
  ;; ---------------------------------------------------------------------------

      (:action walk-to-static-object
    :parameters (?agent - agent ?obj - static-objectt)
    :precondition (and
        (standing ?agent)
        (always-reachable ?obj)
        (not-ready-to-move-to-next-obj ?agent)
    )
    :effect (and
        (close ?agent ?obj)
        (ready-to-move-to-next-obj ?agent)
        (not (not-ready-to-move-to-next-obj ?agent))
    )
  )

  (:action walk-to-surface-object
    :parameters (?agent - agent ?obj - objectt ?surf - surface-objectt)
    :precondition (and
        (standing ?agent)
        (reachable-on-surface ?obj ?surf)
        (not-ready-to-move-to-next-obj ?agent)
    )
    :effect (and
        (close ?agent ?obj)
        (ready-to-move-to-next-obj ?agent)
        (not (not-ready-to-move-to-next-obj ?agent))
    )
  )

  (:action walk-to-inside-container-object
    :parameters (?agent - agent ?obj - objectt ?cont - container-objectt)
    :precondition (and
        (standing ?agent)
        (is-open ?cont)
        (not-ready-to-move-to-next-obj ?agent)
    )
    :effect (and
        (close ?agent ?obj)
        (ready-to-move-to-next-obj ?agent)
        (not (not-ready-to-move-to-next-obj ?agent))
    )
  )

  (:action walk-to-inside-room-object
    :parameters (?agent - agent ?obj - objectt ?loc - room)
    :precondition (and
        (standing ?agent)
        (reachable-inside-room ?obj ?loc)
        (not-ready-to-move-to-next-obj ?agent)
    )
    :effect (and
        (close ?agent ?obj)
        (ready-to-move-to-next-obj ?agent)
        (not (not-ready-to-move-to-next-obj ?agent))
    )
  )

  (:action reset-move
    :parameters (?agent - agent ?source - objectt)
    :precondition (and
        (ready-to-move-to-next-obj ?agent)
        (close ?agent ?source)
    )
    :effect (and
        (not (ready-to-move-to-next-obj ?agent))
        (not-ready-to-move-to-next-obj ?agent)
        (not (close ?agent ?source))
    )
  )

  ;; ---------------------------------------------------------------------------
  ;; SITTING / STANDING
  ;; ---------------------------------------------------------------------------

  (:action sit
    :parameters (?agent - agent ?seat - sittable-objectt)
    :precondition (and
      (standing ?agent)
      (close ?agent ?seat)
    )
    :effect (and
      (sitting ?agent)
      (not (standing ?agent))
    )
  )

  (:action standup
    :parameters (?agent - agent)
    :precondition (sitting ?agent)
    :effect (and
      (not (sitting ?agent))
      (standing ?agent)
    )
  )

  ;; ---------------------------------------------------------------------------
  ;; OBJECT MANIPULATION
  ;; ---------------------------------------------------------------------------

  (:action grab-from-surface
    :parameters (?agent - agent ?obj - grabbable-objectt ?surf - surface-objectt)
    :precondition (and
        (reachable-on-surface ?obj ?surf)
        (close ?agent ?obj)
        (has-free-hand ?agent)
        (on-surface ?obj ?surf)
    )
    :effect (and
        (holding ?agent ?obj)
        (not (has-free-hand ?agent))
        (not (on-surface ?obj ?surf))
    )
  )

  (:action grab-from-container
    :parameters (?agent - agent ?obj - grabbable-objectt ?cont - container-objectt)
    :precondition (and
        (is-open ?cont)
        (close ?agent ?obj)
        (has-free-hand ?agent)
        (in-container ?obj ?cont)
    )
    :effect (and
        (holding ?agent ?obj)
        (not (has-free-hand ?agent))
        (not (in-container ?obj ?cont))
    )
  )

  (:action grab-from-room
    :parameters (?agent - agent ?obj - grabbable-objectt ?loc - room)
    :precondition (and
        (reachable-inside-room ?obj ?loc)
        (close ?agent ?obj)
        (has-free-hand ?agent)
        (in-room ?obj ?loc)
    )
    :effect (and
        (holding ?agent ?obj)
        (not (has-free-hand ?agent))
        (not (in-room ?obj ?loc))
    )
  )

  (:action put-on-surface
    :parameters (?agent - agent ?obj - grabbable-objectt ?surf - surface-objectt)
    :precondition (and
        (holding ?agent ?obj)
        (close ?agent ?surf)
    )
    :effect (and
        (not (holding ?agent ?obj))
        (on-surface ?obj ?surf)
        (has-free-hand ?agent)
        (reachable-on-surface ?obj ?surf)
    )
  )

  (:action put-in-container
    :parameters (?agent - agent ?obj - grabbable-objectt ?cont - container-objectt)
    :precondition (and
        (holding ?agent ?obj)
        (is-open ?cont)
        (close ?agent ?cont)
    )
    :effect (and
        (not (holding ?agent ?obj))
        (in-container ?obj ?cont)
        (has-free-hand ?agent)
    )
  )

  ;; ---------------------------------------------------------------------------
  ;; CONTAINER INTERACTIONS
  ;; ---------------------------------------------------------------------------

  (:action open-container
    :parameters (?agent - agent ?cont - container-objectt)
    :precondition (and
        (is-closed ?cont)
        (always-reachable ?cont)
        (close ?agent ?cont)
        (has-free-hand ?agent)
    )
    :effect (and
        (is-open ?cont)
        (not (is-closed ?cont))
    )
  )

  (:action close-container
    :parameters (?agent - agent ?cont - container-objectt)
    :precondition (and
        (is-open ?cont)
        (close ?agent ?cont)
        (has-free-hand ?agent)
    )
    :effect (and
        (is-closed ?cont)
        (not (is-open ?cont))
    )
  )

  ;; ---------------------------------------------------------------------------
  ;; APPLIANCE INTERACTIONS
  ;; ---------------------------------------------------------------------------

  (:action switchon
    :parameters (?agent - agent ?app - switchable-objectt)
    :precondition (and
        (close ?agent ?app)
        (off ?app)
    )
    :effect (and
        (on ?app)
        (not (off ?app))
    )
  )

  (:action switchoff
    :parameters (?agent - agent ?app - switchable-objectt)
    :precondition (and
        (on ?app)
        (close ?agent ?app)
    )
    :effect (and
        (not (on ?app))
        (off ?app)
    )
  )
)
